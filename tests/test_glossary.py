import os

from hindi2pt.cli import main
from hindi2pt.glossary import Glossary, GlossaryBackend
from hindi2pt.translate import DummyBackend

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_protect_and_restore():
    g = Glossary([("मुंबई", "Mumbai"), ("पनीर", "paneer"), ("Technical Guruji", None)])
    text, slots = g.protect("मुंबई में पनीर खाओ Technical Guruji के साथ")
    assert "मुंबई" not in text and "⟦0⟧" in text
    assert sorted(slots) == ["Mumbai", "Technical Guruji", "paneer"]
    assert g.restore(text, slots) == "Mumbai में paneer खाओ Technical Guruji के साथ"
    assert g.restore("Coma ⟦1⟧ em ⟦0⟧ e ⟦9⟧", ["A", "B"]) == "Coma B em A e "
    assert g.protect("मुंबईकर")[0] == "मुंबईकर", "so palavra inteira"


def test_longest_term_wins():
    g = Glossary([("दिल्ली", "Delhi"), ("नई दिल्ली", "Nova Delhi")])
    text, slots = g.protect("नई दिल्ली और दिल्ली")
    assert slots == ["Nova Delhi", "Delhi"]


def test_load_file_and_backend(tmpdir):
    path = os.path.join(str(tmpdir), "glossario.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# nomes\nमुंबई = Mumbai\nपनीर = paneer   # comida\nTechnical Guruji\n\n")
    g = Glossary.load(path)
    assert len(g) == 3
    backend = GlossaryBackend(DummyBackend(), g)
    assert backend.name == "dummy"
    out = backend.translate_batch(["मुंबई में पनीर", "sem termo"])
    assert out == ["[pt] Mumbai में paneer", "[pt] sem termo"]

    class Dropper(object):
        name = "dropper"

        def translate_batch(self, lines):
            return ["perdeu os marcadores"] * len(lines)

    assert GlossaryBackend(Dropper(), g).translate_batch(["मुंबई"]) == ["perdeu os marcadores"]


def test_cli_with_glossary(tmpdir, capsys):
    path = os.path.join(str(tmpdir), "g.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("खास = ESPECIAL\n")
    assert main([os.path.join(FIXTURES, "sample.hi.vtt"), "-o", str(tmpdir), "-b", "dummy", "--glossary", path]) == 0
    assert "glossario: 1 termo" in capsys.readouterr().out
    with open(os.path.join(str(tmpdir), "sample.pt-BR.srt"), encoding="utf-8") as f:
        assert "ESPECIAL" in f.read()
