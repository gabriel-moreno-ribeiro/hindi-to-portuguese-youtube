import os

import pytest

from hindi2pt import subtitles as S
from hindi2pt.cli import main
from hindi2pt.review import export_tsv, import_tsv

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_export_and_import_round_trip():
    original = [S.Cue(1, 2.5, "नमस्ते"), S.Cue(3, 4, "दुनिया\nफिर")]
    translated = [S.Cue(1, 2.5, "Olá"), S.Cue(3, 4, "mundo\nde novo")]
    tsv = export_tsv(original, translated)
    lines = tsv.splitlines()
    assert lines[0] == "n\tinicio\tfim\thindi\tportugues"
    assert lines[2] == "2\t00:00:03,000\t00:00:04,000\tदुनिया / फिर\tmundo / de novo"
    back = import_tsv(tsv)
    assert back == translated
    edited = tsv.replace("Olá", "Oi, tudo bem com vocês aí do outro lado do mundo inteiro hoje").replace("mundo / de novo", "")
    back = import_tsv(edited)
    assert len(back) == 1 and "\n" in back[0].text, "linha comprida e quebrada; linha vazia some"
    with pytest.raises(ValueError):
        import_tsv("n\tinicio\tfim\thindi\tportugues\n1\t00:00:01,000\n")
    with pytest.raises(ValueError):
        import_tsv("n\tinicio\tfim\thindi\tportugues\n")


def test_review_flags_on_the_cli(tmpdir, capsys):
    src = os.path.join(FIXTURES, "sample.hi.vtt")
    tsv = os.path.join(str(tmpdir), "revisao.tsv")
    assert main([src, "-o", str(tmpdir), "-b", "dummy", "--no-cache", "--review", tsv]) == 0
    assert "revisao: " in capsys.readouterr().out and os.path.exists(tsv)
    with open(tsv, encoding="utf-8") as f:
        text = f.read()
    assert "[pt]" in text and "आज" in text
    with open(tsv, "w", encoding="utf-8") as f:
        f.write(text.replace("[pt]", "REVISADO"))
    assert main([src, "-o", str(tmpdir), "-b", "dummy", "--apply-review", tsv]) == 0
    with open(os.path.join(str(tmpdir), "sample.pt-BR.srt"), encoding="utf-8") as f:
        final = f.read()
    assert "REVISADO" in final and "[pt]" not in final
