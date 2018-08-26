"""Os tradutores. Cada backend traduz um lote de linhas; o ``Translator`` cuida de
dividir em lotes e de nao mandar a mesma coisa duas vezes.

- ``google``: a API paga do Google Cloud Translation (v2). Precisa de uma chave, mas
  os primeiros 500 mil caracteres por mes sao de graca, o que da uns 50 videos.
- ``googletrans``: a biblioteca nao oficial que usa o site do Google Translate.
  De graca, sem chave, e para de funcionar de vez em quando.
- ``dummy``: sem rede; marca as linhas pra dar pra testar o resto.
"""
import json
import urllib.parse
import urllib.request

GOOGLE_URL = "https://translation.googleapis.com/language/translate/v2"


class DummyBackend(object):
    """Marca cada linha pra gente conferir o encanamento sem rede."""

    name = "dummy"

    def __init__(self):
        self.calls = 0

    def translate_batch(self, lines):
        self.calls += 1
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
    """Manda as linhas em lotes e devolve as traducoes na mesma ordem."""

    def __init__(self, backend, batch_size=40):
        self.backend = backend
        self.batch_size = batch_size

    def translate(self, lines, progress=None):
        out = []
        for start in range(0, len(lines), self.batch_size):
            batch = lines[start:start + self.batch_size]
            translated = self.backend.translate_batch(batch)
            if len(translated) != len(batch):
                raise RuntimeError(f"o tradutor devolveu {len(translated)} linhas pra {len(batch)}")
            out.extend(translated)
            if progress:
                progress(len(out), len(lines))
        return out
