import os
import subprocess

import pytest

from hindi2pt import dub as D
from hindi2pt import subtitles as S


class FakeFfmpeg(object):
    """Finge o ffmpeg/ffprobe: 'toca' clipes com uma duracao que a gente escolhe."""

    def __init__(self, durations):
        self.durations = durations   # nome do arquivo -> segundos
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[0] == "ffprobe":
            name = os.path.basename(cmd[-1])
            return subprocess.CompletedProcess(cmd, 0, str(self.durations.get(name, 1.0)).encode(), b"")
        with open(cmd[-1], "wb") as f:
            f.write(b"fake")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")


def test_dub_builds_the_timeline_and_speeds_up_long_speech(tmpdir):
    srt = os.path.join(str(tmpdir), "v.pt-BR.srt")
    with open(srt, "w", encoding="utf-8") as f:
        f.write(S.to_srt([S.Cue(0, 1, "oi"), S.Cue(1, 4, "uma frase\ncomprida"), S.Cue(10, 11, "fim")]))
    spoken = []

    def fake_speak(text, path):
        spoken.append(text)
        with open(path, "wb") as f:
            f.write(b"mp3")

    ff = FakeFfmpeg({"00000.raw.mp3": 0.8, "00001.raw.mp3": 12.0, "00002.raw.mp3": 1.0})
    out = D.dub(srt, os.path.join(str(tmpdir), "v.mp3"), log=lambda _: None, speak=fake_speak, run=ff, which=lambda n: "/usr/bin/" + n)
    assert out.endswith("v.mp3") and os.path.exists(out)
    assert spoken == ["oi", "uma frase comprida", "fim"]
    atempo = [c for c in ff.calls if c[0] == "ffmpeg" and "-filter:a" in c]
    # a segunda fala tem 9 s ate a proxima legenda e o clipe tem 12 s: acelera 12/9
    assert len(atempo) == 1 and atempo[0][atempo[0].index("-filter:a") + 1] == "atempo=1.333"
    final = ff.calls[-1]
    assert "amix=inputs=4:normalize=0[out]" in final[final.index("-filter_complex") + 1]
    assert "adelay=1000|1000" in final[final.index("-filter_complex") + 1]


def test_fit_clip_only_speeds_up_what_does_not_fit(tmpdir):
    src = os.path.join(str(tmpdir), "a.mp3")
    with open(src, "wb") as f:
        f.write(b"x")
    ff = FakeFfmpeg({"a.mp3": 2.0})
    assert D.fit_clip(src, os.path.join(str(tmpdir), "b.mp3"), 3.0, run=ff) == 1.0
    assert not any(c[0] == "ffmpeg" for c in ff.calls)
    assert D.fit_clip(src, os.path.join(str(tmpdir), "c.mp3"), 1.5, run=ff) == pytest.approx(1.333, abs=0.001)
    assert D.fit_clip(src, os.path.join(str(tmpdir), "d.mp3"), 0.5, run=ff) == 1.6, "nunca acima de 1.6x"


def test_dub_needs_ffmpeg_and_a_subtitle(tmpdir):
    with pytest.raises(RuntimeError):
        D.dub("x.srt", "y.mp3", which=lambda n: None)
    empty = os.path.join(str(tmpdir), "e.srt")
    with open(empty, "w", encoding="utf-8") as f:
        f.write("")
    with pytest.raises(RuntimeError):
        D.dub(empty, "y.mp3", which=lambda n: "/bin/" + n)


def test_burn_builds_the_ffmpeg_command(tmpdir):
    ff = FakeFfmpeg({})
    out = D.burn("video.mp4", "C:\\legendas\\v.srt", os.path.join(str(tmpdir), "o.mp4"), audio="dub.mp3", log=lambda _: None, run=ff, which=lambda n: "/bin/" + n)
    cmd = ff.calls[0]
    assert cmd[:4] == ["ffmpeg", "-y", "-i", "video.mp4"] and "dub.mp3" in cmd and "-map" in cmd
    assert cmd[cmd.index("-vf") + 1] == "subtitles='C\\:/legendas/v.srt'"
    assert out.endswith("o.mp4")
