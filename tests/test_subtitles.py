import os

import pytest

from hindi2pt import subtitles as S

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def test_time_round_trip():
    assert S.parse_time("01:02:03,450") == 3723.45
    assert S.parse_time("00:00:05.5") == 5.5
    assert S.parse_time("02:03.250") == 123.25
    assert S.format_time(3723.45) == "01:02:03,450"
    assert S.format_time(0.0012, ".") == "00:00:00.001"
    with pytest.raises(ValueError):
        S.parse_time("nope")


def test_parse_srt_and_vtt():
    srt = "1\n00:00:01,000 --> 00:00:02,000\nनमस्ते\n\n2\n00:00:02,500 --> 00:00:04,000\n<i>दुनिया</i>\nदूसरी लाइन\n"
    cues = S.parse(srt)
    assert [c.text for c in cues] == ["नमस्ते", "दुनिया\nदूसरी लाइन"]
    assert cues[1].start == 2.5 and cues[1].end == 4.0
    vcues = S.parse(read("sample.hi.vtt"))
    assert len(vcues) == 6
    assert vcues[0].start == 0.5
    assert "<" not in vcues[0].text
    assert S.parse("WEBVTT\n\nNOTE hello\nmore\n\n00:01.000 --> 00:02.000\nx\n")[0].text == "x"


def test_srt_writer_round_trip():
    cues = [S.Cue(1.0, 2.5, "a"), S.Cue(3.0, 4.0, "b\nc")]
    text = S.to_srt(cues)
    assert text.startswith("1\n00:00:01,000 --> 00:00:02,500\na\n")
    assert S.parse(text) == cues
    assert S.parse(S.to_vtt(cues)) == cues
    assert cues[0].copy(text="z") == S.Cue(1.0, 2.5, "z") and cues[0].duration == 1.5
