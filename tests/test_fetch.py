import json
import os
import subprocess

import pytest

from hindi2pt import cli
from hindi2pt.fetch import fetch_subtitles, is_playlist, is_url, list_videos, video_id

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_video_id():
    assert video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1") == "dQw4w9WgXcQ"
    assert video_id("https://youtu.be/abc123xyz") == "abc123xyz"
    assert is_url("https://youtu.be/x") and not is_url("video.vtt")
    assert is_playlist("https://www.youtube.com/playlist?list=PL123")
    assert is_playlist("https://www.youtube.com/channel/UCxyz/videos")
    assert not is_playlist("https://www.youtube.com/watch?v=abc")


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

    def missing(cmd, **kw):
        raise FileNotFoundError("youtube-dl")

    with pytest.raises(RuntimeError):
        fetch_subtitles("https://youtu.be/nosubs1", str(tmpdir), run=missing)


def test_list_videos_reads_flat_playlist_json():
    lines = [json.dumps({"id": "aaa111bbb", "title": "um"}), "", "lixo que nao e json",
             json.dumps({"url": "https://www.youtube.com/watch?v=ccc333ddd"})]

    def fake_run(cmd, **kw):
        assert cmd[:2] == ["youtube-dl", "--playlist-end"] and cmd[2] == "2"
        return subprocess.CompletedProcess(cmd, 0, "\n".join(lines).encode("utf-8"), b"")

    assert list_videos("https://www.youtube.com/playlist?list=PL1", run=fake_run, limit=2) == [
        "https://www.youtube.com/watch?v=aaa111bbb", "https://www.youtube.com/watch?v=ccc333ddd"]
    with pytest.raises(RuntimeError):
        list_videos("https://www.youtube.com/playlist?list=PL1", run=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, b"", b""))


def test_playlist_run_skips_broken_videos(tmpdir, capsys, monkeypatch):
    monkeypatch.setattr(cli, "list_videos", lambda url, limit=None: ["https://youtu.be/ok1ok1ok1", "https://youtu.be/bad2bad2b"])

    def fake_fetch(url, out_dir, log=print):
        if "bad" in url:
            raise RuntimeError("sem legenda")
        path = os.path.join(out_dir, "ok1ok1ok1.hi.vtt")
        with open(os.path.join(FIXTURES, "sample.hi.vtt"), encoding="utf-8") as src, open(path, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        return path

    monkeypatch.setattr(cli, "fetch_subtitles", fake_fetch)
    assert cli.main(["https://www.youtube.com/playlist?list=PL1", "-o", str(tmpdir), "-b", "dummy"]) == 0
    out = capsys.readouterr().out
    assert "playlist: 2 video(s)" in out and "pulei: sem legenda" in out and "1 traduzido(s), 1 pulado(s)" in out
    assert os.path.exists(os.path.join(str(tmpdir), "ok1ok1ok1.pt-BR.srt"))
