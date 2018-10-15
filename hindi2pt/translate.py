"""Os tradutores. Cada backend traduz um lote de linhas; o ``Translator`` cuida de
dividir em lotes, guardar o que ja foi traduzido num cache em disco e tentar de novo
quando a rede falha (o googletrans falha bastante).

- ``google``: a API paga do Google Cloud Translation (v2). Precisa de uma chave, mas
  os primeiros 500 mil caracteres por mes sao de graca, o que da uns 50 videos.
- ``googletrans``: a biblioteca nao oficial que usa o site do Google Translate.
  De graca, sem chave, e para de funcionar de vez em quando.
- ``dummy``: sem rede; marca as linhas pra dar pra testar o resto.
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

GOOGLE_URL = "https://translation.googleapis.com/language/translate/v2"


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
            raise RuntimeError("pip install googletrans (ou use -b google com uma chave)")
        self._gt = Translator()
        self.source = source
        self.target = target

    def translate_batch(self, lines):  # pragma: no cover - rede
        return [self._gt.translate(line, src=self.source, dest=self.target).text for line in lines]


def make_backend(name, key=None):
    if name == "dummy":
        return DummyBackend()
    if name == "google":
        return GoogleCloudBackend(key)
    if name == "googletrans":
        return GoogletransBackend()
    raise ValueError(f"backend desconhecido {name!r} (use google, googletrans ou dummy)")


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
