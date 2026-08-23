"""Os tradutores. Cada backend traduz um lote de linhas; o ``Translator`` cuida de
dividir em lotes, guardar o que ja foi traduzido num cache em disco e tentar de novo
quando a rede falha.

Os de 2018:
- ``google``: a API paga do Google Cloud Translation (v2). Precisa de uma chave.
- ``googletrans``: a biblioteca nao oficial que usa o site do Google Translate.
- ``dummy``: sem rede; marca as linhas pra dar pra testar o resto.

Os de 2026 (atualizacao):
- ``argos``: offline e de graca, com o argostranslate (hindi -> ingles -> portugues
  quando nao tem modelo direto). Mediano, mas nao depende de ninguem.
- ``openai`` / ``anthropic``: um LLM recebe o lote inteiro com as linhas numeradas,
  entao ve o contexto das frases vizinhas e da um portugues muito melhor.
"""
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request

GOOGLE_URL = "https://translation.googleapis.com/language/translate/v2"

SYSTEM_PROMPT = (
    "You translate Hindi subtitles from YouTube videos into natural Brazilian Portuguese. "
    "Keep the meaning, the tone and the slang level; do not add explanations. "
    "The input is a numbered list of lines; answer with the same numbers, one line each, "
    "and nothing else."
)


class DummyBackend(object):
    """Marca cada linha pra gente conferir o encanamento sem rede."""

    name = "dummy"

    def __init__(self, fail_first=0):
        self.calls = 0
        self.fail_first = fail_first

    def translate_batch(self, lines):
        self.calls += 1
        if self.calls <= self.fail_first:
            raise RuntimeError("falha simulada")
        return [f"[pt] {line}" for line in lines]


class GoogleCloudBackend(object):
    """Google Cloud Translation v2 por REST, so com urllib (sem SDK)."""

    name = "google"

    def __init__(self, key, source="hi", target="pt", post=None):
        if not key:
            raise RuntimeError("passe --key ou a variavel GOOGLE_TRANSLATE_KEY")
        self.key = key
        self.source = source
        self.target = target
        self.post = post or self._http_post

    def translate_batch(self, lines):
        payload = {"q": lines, "source": self.source, "target": self.target, "format": "text"}
        data = self.post(f"{GOOGLE_URL}?key={urllib.parse.quote(self.key)}", payload)
        try:
            return [t["translatedText"] for t in data["data"]["translations"]]
        except (KeyError, TypeError):
            raise RuntimeError(f"resposta estranha do Google: {json.dumps(data)[:200]}")

    @staticmethod
    def _http_post(url, payload):  # pragma: no cover - rede
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)


class GoogletransBackend(object):
    """A biblioteca googletrans (pip install googletrans). Funciona ate o Google mudar alguma coisa."""

    name = "googletrans"

    def __init__(self, source="hi", target="pt"):
        try:
            from googletrans import Translator
        except ImportError:
            raise RuntimeError("pip install googletrans (ou use -b argos, que e offline)")
        self._gt = Translator()
        self.source = source
        self.target = target

    def translate_batch(self, lines):  # pragma: no cover - rede
        return [self._gt.translate(line, src=self.source, dest=self.target).text for line in lines]


class ArgosBackend(object):
    """Traducao offline com o argostranslate; baixa os modelos na primeira vez."""

    name = "argos"

    def __init__(self, source="hi", target="pt"):
        try:
            import argostranslate.package
            import argostranslate.translate
        except ImportError:
            raise RuntimeError("pip install argostranslate  (modelos offline, sem chave nenhuma)")
        self._translate = argostranslate.translate
        self._package = argostranslate.package
        self.source, self.target = source, target
        self.pivot = False
        self._ensure_models()

    def _ensure_models(self):  # pragma: no cover - rede
        installed = {(p.from_code, p.to_code) for p in self._package.get_installed_packages()}
        needed = [(self.source, self.target)]
        if (self.source, self.target) not in installed:
            needed = [(self.source, "en"), ("en", self.target)]
            self.pivot = True
        self._package.update_package_index()
        available = self._package.get_available_packages()
        for pair in needed:
            if pair in installed:
                continue
            match = next((p for p in available if (p.from_code, p.to_code) == pair), None)
            if match is None:
                raise RuntimeError(f"nao tem modelo do argos pra {pair}")
            self._package.install_from_path(match.download())

    def translate_batch(self, lines):  # pragma: no cover - modelos
        out = []
        for line in lines:
            if self.pivot:
                text = self._translate.translate(line, self.source, "en")
                text = self._translate.translate(text, "en", self.target)
            else:
                text = self._translate.translate(line, self.source, self.target)
            out.append(text)
        return out


def _numbered(lines):
    return "\n".join(f"{i + 1}. {line.replace(chr(10), ' ')}" for i, line in enumerate(lines))


def parse_numbered(answer, expected):
    """Le as linhas '1. ...' de volta; tolera numero faltando no fim."""
    found = {}
    for line in answer.splitlines():
        m = re.match(r"\s*(\d+)\s*[.)\-:]\s*(.*)", line)
        if m:
            found[int(m.group(1))] = m.group(2).strip()
    if len(found) < expected:
        raise ValueError(f"o modelo devolveu {len(found)} de {expected} linhas")
    return [found.get(i + 1, "") for i in range(expected)]


class LlmBackend(object):
    """O encanamento comum das APIs de chat: so a chamada HTTP muda."""

    def __init__(self, call, name):
        self._call = call
        self.name = name

    def translate_batch(self, lines):
        answer = self._call(SYSTEM_PROMPT, _numbered(lines))
        return parse_numbered(answer, len(lines))


def openai_backend(model="gpt-4o-mini"):  # pragma: no cover - rede
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("defina OPENAI_API_KEY")

    def call(system, user):
        body = json.dumps({"model": model, "temperature": 0.2,
                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]["content"]

    return LlmBackend(call, "openai")


def anthropic_backend(model="claude-sonnet-5"):  # pragma: no cover - rede
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("defina ANTHROPIC_API_KEY")

    def call(system, user):
        body = json.dumps({"model": model, "max_tokens": 4096, "system": system,
                           "messages": [{"role": "user", "content": user}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return "".join(part.get("text", "") for part in json.load(r)["content"])

    return LlmBackend(call, "anthropic")


BACKENDS = ("argos", "openai", "anthropic", "google", "googletrans", "dummy")


def make_backend(name, key=None):
    if name == "dummy":
        return DummyBackend()
    if name == "google":
        return GoogleCloudBackend(key)
    if name == "googletrans":
        return GoogletransBackend()
    if name == "argos":
        return ArgosBackend()
    if name == "openai":
        return openai_backend()
    if name == "anthropic":
        return anthropic_backend()
    raise ValueError(f"backend desconhecido {name!r} (use {', '.join(BACKENDS)})")


class Translator(object):
    """Manda as linhas em lotes, guarda o resultado em disco e tenta de novo quando falha."""

    def __init__(self, backend, cache_path=None, batch_size=40, retries=3, sleep=time.sleep):
        self.backend = backend
        self.cache_path = cache_path
        self.batch_size = batch_size
        self.retries = retries
        self.sleep = sleep
        self.cache = {}
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                self.cache = json.load(f)

    def _key(self, line):
        return hashlib.sha1((self.backend.name + "\0" + line).encode("utf-8")).hexdigest()

    def translate(self, lines, progress=None):
        result = [self.cache.get(self._key(l)) for l in lines]
        todo = [i for i, r in enumerate(result) if r is None]
        done = len(lines) - len(todo)
        for start in range(0, len(todo), self.batch_size):
            idx = todo[start:start + self.batch_size]
            batch = [lines[i] for i in idx]
            translated = self._with_retries(batch)
            for i, text in zip(idx, translated):
                result[i] = text
                self.cache[self._key(lines[i])] = text
            done += len(idx)
            if progress:
                progress(done, len(lines))
            self._save()
        return [r or "" for r in result]

    def _with_retries(self, batch):
        last = None
        for attempt in range(self.retries):
            try:
                out = self.backend.translate_batch(batch)
                if len(out) != len(batch):
                    raise ValueError(f"o tradutor devolveu {len(out)} linhas pra {len(batch)}")
                return out
            except Exception as e:
                last = e
                self.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"a traducao falhou {self.retries} vezes: {last}")

    def _save(self):
        if self.cache_path:
            folder = os.path.dirname(os.path.abspath(self.cache_path))
            os.makedirs(folder, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=0)
