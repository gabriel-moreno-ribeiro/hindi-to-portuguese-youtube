import os

from hindi2pt import subtitles as S
from hindi2pt.cli import main

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def read_srt(folder):
    with open(os.path.join(folder, "sample.pt-BR.srt"), encoding="utf-8") as f:
        return S.parse(f.read())


def test_offset_scale_and_bilingual_from_the_cli(tmpdir):
    src = os.path.join(FIXTURES, "sample.hi.vtt")
    assert main([src, "-o", str(tmpdir), "-b", "dummy", "--no-cache"]) == 0
    plain = read_srt(str(tmpdir))
    assert main([src, "-o", str(tmpdir), "-b", "dummy", "--no-cache", "--offset", "2", "--scale", "2", "--bilingual"]) == 0
    moved = read_srt(str(tmpdir))
    assert len(moved) == len(plain)
    assert moved[0].start == plain[0].start * 2 + 2
    assert "\n" in moved[0].text and "[pt]" in moved[0].text and "आज" in moved[0].text
    assert main([src, "-o", str(tmpdir), "-b", "dummy", "--scale", "0"]) == 1
