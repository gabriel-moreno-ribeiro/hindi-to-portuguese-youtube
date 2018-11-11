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


def test_rolling_captions_are_deduplicated():
    cues = S.parse(read("sample.hi.vtt"))
    flat = S.dedupe_rolling(cues)
    assert [c.text for c in flat] == ["आज हम बात करेंगे", "एक बहुत खास चीज़ के बारे में।", "चलिए शुरू करते हैं", "यह वीडियो के अंत तक देखिए"]
    normal = S.normalize(cues)
    texts = [c.text for c in normal]
    assert texts[0] == "आज हम बात करेंगे एक बहुत खास चीज़ के बारे में."
    assert len(normal) == 2, texts
    for a, b in zip(normal, normal[1:]):
        assert a.end <= b.start
    assert all(c.duration >= 0.8 for c in normal)


def test_merge_respects_limits():
    cues = [S.Cue(0, 1, "a" * 60), S.Cue(1.2, 2, "b" * 60)]
    assert len(S.merge_short(cues)) == 2, "comprido demais pra juntar"
    cues = [S.Cue(0, 1, "hello"), S.Cue(5, 6, "world")]
    assert len(S.merge_short(cues)) == 2, "pausa longa"
    cues = [S.Cue(0, 1, "end."), S.Cue(1.1, 2, "next")]
    assert len(S.merge_short(cues)) == 2, "fim de frase"
    cues = [S.Cue(0, 1, "one"), S.Cue(1.1, 2, "two")]
    assert S.merge_short(cues)[0].text == "one two"


def test_fix_overlaps_and_minimum_duration():
    cues = [S.Cue(0, 2.5, "a"), S.Cue(2.0, 2.3, "b"), S.Cue(2.4, 9, "c")]
    fixed = S.fix_overlaps(cues)
    assert fixed[0].end == 2.0, "a primeira para onde a segunda comeca"
    assert fixed[1].end == 2.4, "a segunda estica ate onde da (a proxima comeca em 2.4)"
    assert fixed[2].end == 9
    assert S.fix_overlaps([S.Cue(0, 0.1, "x")])[0].end == 0.8


def test_wrap_balances_two_lines():
    assert S.wrap("curta") == "curta"
    long = "esta é uma frase bem comprida que não cabe em uma linha só da tela"
    lines = S.wrap(long).split("\n")
    assert len(lines) == 2 and abs(len(lines[0]) - len(lines[1])) <= 12
    assert " ".join(lines) == long


def test_reading_speed_stretches_fast_cues():
    cues = [S.Cue(0, 1, "x" * 40), S.Cue(3, 4, "y" * 40), S.Cue(4.2, 5, "z" * 10), S.Cue(10, 11, "w" * 100)]
    fixed, too_fast = S.fit_reading_speed(cues, max_cps=20)
    assert fixed[0].end == 2.0, "40 caracteres precisam de 2 s"
    assert fixed[1].end == pytest.approx(4.1), "so pode ir ate 0.1 s antes da proxima"
    assert fixed[2].end == 5, "ja estava lento o bastante"
    assert fixed[3].end == 15.0
    assert too_fast == [1]
    assert S.chars_per_second(S.Cue(0, 0, "ab")) == float("inf")
