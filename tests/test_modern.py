"""Os pedacos da atualizacao de 2026: LLMs, yt-dlp e as vozes."""
import os
import subprocess

import pytest

from hindi2pt import dub as D
from hindi2pt.cli import main
from hindi2pt.fetch import fetch_subtitles, is_playlist, list_videos, video_id
from hindi2pt.translate import BACKENDS, LlmBackend, make_backend, parse_numbered

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_llm_backend_parses_numbered_answers():
    seen = {}

    def fake_call(system, user):
        seen["user"] = user
        return "1. Olá mundo\n2) Tudo bem?\n3 - fim"

    backend = LlmBackend(fake_call, "fake")
    assert backend.translate_batch(["नमस्ते दुनिया", "क्या हाल है", "अंत"]) == ["Olá mundo", "Tudo bem?", "fim"]
    assert seen["user"].startswith("1. नमस्ते दुनिया\n2. क्या हाल है")
    with pytest.raises(ValueError):
        parse_numbered("1. only one", 2)


def test_backend_names():
    assert BACKENDS[0] == "argos" and "googletrans" in BACKENDS
    with pytest.raises(ValueError):
        make_backend("nope")
    for name in ("openai", "anthropic"):
        os.environ.pop({"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[name], None)
        with pytest.raises(RuntimeError):
            make_backend(name)


def test_shorts_and_handles():
    assert video_id("https://www.youtube.com/shorts/Z9x-8_qwe") == "Z9x-8_qwe"
    assert is_playlist("https://www.youtube.com/@canal/videos")


def test_old_youtube_dl_path_still_works_without_ytdlp(tmpdir):
    def fake_run(cmd, **kw):
        with open(os.path.join(str(tmpdir), "abc123xyz.hi.vtt"), "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n00:01.000 --> 00:02.000\nx\n")
        return subprocess.CompletedProcess(cmd, 0, b'{"id": "abc123xyz"}\n', b"")

    path = fetch_subtitles("https://youtu.be/abc123xyz", str(tmpdir), log=lambda _: None, run=fake_run, ytdlp=lambda: None)
    assert path.endswith("abc123xyz.hi.vtt")
    assert list_videos("https://www.youtube.com/playlist?list=PL1", run=fake_run, ytdlp=lambda: None) == ["https://www.youtube.com/watch?v=abc123xyz"]


def test_ytdlp_module_is_used_when_present(tmpdir):
    class FakeYDL(object):
        opts = []

        def __init__(self, opts):
            FakeYDL.opts.append(opts)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            if download:
                with open(os.path.join(str(tmpdir), "abc123xyz.hi.vtt"), "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n00:01.000 --> 00:02.000\nx\n")
                return {}
            return {"entries": [{"id": "abc123xyz"}, None, {"url": "https://youtu.be/def456uvw"}]}

    class FakeModule(object):
        YoutubeDL = FakeYDL

    path = fetch_subtitles("https://youtu.be/abc123xyz", str(tmpdir), log=lambda _: None, ytdlp=lambda: FakeModule)
    assert path.endswith("abc123xyz.hi.vtt") and FakeYDL.opts[0]["writeautomaticsub"] is True
    assert list_videos("https://www.youtube.com/playlist?list=PL1", limit=5, ytdlp=lambda: FakeModule) == [
        "https://www.youtube.com/watch?v=abc123xyz", "https://youtu.be/def456uvw"]
    assert FakeYDL.opts[-1]["playlistend"] == 5


def test_voices_and_cli_default_backend(tmpdir, capsys):
    assert set(D.VOICES) == {"gtts", "edge"}
    assert main([os.path.join(FIXTURES, "sample.hi.vtt"), "-o", str(tmpdir), "-b", "dummy", "--voice", "gtts"]) == 0
    assert "pronto: 2 legendas" in capsys.readouterr().out
