import os
import subprocess

import pytest

from hindi2pt.cli import main
from hindi2pt.fetch import fetch_subtitles, is_url, video_id

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_video_id():
    assert video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1") == "dQw4w9WgXcQ"
    assert video_id("https://youtu.be/abc123xyz") == "abc123xyz"
    assert is_url("https://youtu.be/x") and not is_url("video.vtt")


def test_fetch_calls_youtube_dl_and_finds_the_file(tmpdir):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        with open(os.path.join(str(tmpdir), "abc123xyz.hi.vtt"), "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n00:01.000 --> 00:02.000\nx\n")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    path = fetch_subtitles("https://youtu.be/abc123xyz", str(tmpdir), log=lambda _: None, run=fake_run)
    assert path.endswith("abc123xyz.hi.vtt")
    assert calls[0][0] == "youtube-dl" and "--write-auto-sub" in calls[0] and calls[0][-1] == "https://youtu.be/abc123xyz"

    def failing(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 1, b"", b"ERROR: video unavailable")

    with pytest.raises(RuntimeError):
        fetch_subtitles("https://youtu.be/zzz999", str(tmpdir), run=failing)

    def no_subs(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    with pytest.raises(RuntimeError):
        fetch_subtitles("https://youtu.be/nosubs1", str(tmpdir), run=no_subs)


def test_cli_converts_a_local_vtt(tmpdir, capsys):
    assert main([os.path.join(FIXTURES, "sample.hi.vtt"), "-o", str(tmpdir)]) == 0
    assert "6 legendas" in capsys.readouterr().out
    assert os.path.exists(os.path.join(str(tmpdir), "sample.hi.srt"))
    assert main([os.path.join(FIXTURES, "nao-existe.vtt"), "-o", str(tmpdir)]) == 1
