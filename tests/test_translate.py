import os

import pytest

from hindi2pt.cli import main
from hindi2pt.translate import DummyBackend, GoogleCloudBackend, Translator, make_backend

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_translator_batches_in_order():
    backend = DummyBackend()
    seen = []
    t = Translator(backend, batch_size=2)
    out = t.translate(["a", "b", "c", "d", "e"], progress=lambda d, n: seen.append((d, n)))
    assert out == ["[pt] a", "[pt] b", "[pt] c", "[pt] d", "[pt] e"]
    assert backend.calls == 3 and seen == [(2, 5), (4, 5), (5, 5)]


def test_translator_rejects_a_backend_that_loses_lines():
    class Lossy(object):
        name = "lossy"

        def translate_batch(self, lines):
            return lines[:-1]

    with pytest.raises(RuntimeError):
        Translator(Lossy()).translate(["a", "b"])


def test_google_cloud_backend_speaks_the_v2_api():
    posted = []

    def fake_post(url, payload):
        posted.append((url, payload))
        return {"data": {"translations": [{"translatedText": "Olá mundo"}, {"translatedText": "Tudo bem?"}]}}

    g = GoogleCloudBackend("KEY", post=fake_post)
    assert g.translate_batch(["नमस्ते दुनिया", "क्या हाल है"]) == ["Olá mundo", "Tudo bem?"]
    url, payload = posted[0]
    assert url.endswith("?key=KEY") and payload["q"] == ["नमस्ते दुनिया", "क्या हाल है"]
    assert payload["source"] == "hi" and payload["target"] == "pt"
    with pytest.raises(RuntimeError):
        GoogleCloudBackend("KEY", post=lambda u, p: {"error": "quota"}).translate_batch(["x"])
    with pytest.raises(RuntimeError):
        GoogleCloudBackend(None)


def test_make_backend():
    assert make_backend("dummy").name == "dummy"
    with pytest.raises(ValueError):
        make_backend("nope")


def test_cli_translates_a_local_file(tmpdir, capsys):
    assert main([os.path.join(FIXTURES, "sample.hi.vtt"), "-o", str(tmpdir), "-b", "dummy"]) == 0
    out = capsys.readouterr().out
    assert "6 cues viraram 2" in out and "pronto: 2 legendas" in out
    with open(os.path.join(str(tmpdir), "sample.pt-BR.srt"), encoding="utf-8") as f:
        assert f.read().count("[pt]") == 2
    assert main([os.path.join(FIXTURES, "sample.hi.vtt"), "-o", str(tmpdir), "-b", "dummy", "--raw"]) == 0
    assert "pronto: 6 legendas" in capsys.readouterr().out
    assert main([os.path.join(FIXTURES, "sample.hi.vtt"), "-o", str(tmpdir), "-b", "nope"]) == 1
    assert "desconhecido" in capsys.readouterr().err
