"""Glossario: nomes e termos que o tradutor automatico nao pode inventar.

Um arquivo de texto com ``termo = traducao`` por linha (``termo`` sozinho quer dizer
"deixa como esta"). Antes de traduzir, cada termo vira um marcador que o tradutor
nao mexe (``⟦3⟧``); depois o marcador vira a traducao escolhida. Assim "Mumbai" nao
vira "Bombaim", "paneer" nao vira "queijo" e o nome do canal continua o nome do canal.
"""
import re

MARK_RE = re.compile(r"⟦(\d+)⟧")   # ⟦n⟧


class Glossary(object):
    def __init__(self, entries=None):
        self.entries = []   # lista de (termo, traducao), os mais longos primeiro
        for term, translation in (entries or []):
            self.add(term, translation)

    def add(self, term, translation=None):
        term = term.strip()
        if not term:
            return
        self.entries.append((term, (translation or term).strip()))
        self.entries.sort(key=lambda e: -len(e[0]))

    @classmethod
    def load(cls, path):
        g = cls()
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                if "=" in line:
                    term, translation = line.split("=", 1)
                    g.add(term, translation)
                else:
                    g.add(line)
        return g

    def protect(self, text):
        """Troca cada termo por um marcador. Devolve (texto, lista de traducoes por marcador)."""
        slots = []

        def replace(m):
            slots.append(self._translation_for(m.group(0)))
            return "⟦%d⟧" % (len(slots) - 1)

        for term, _ in self.entries:
            text = re.sub(r"(?<!\w)" + re.escape(term) + r"(?!\w)", replace, text)
        return text, slots

    def restore(self, text, slots):
        def replace(m):
            i = int(m.group(1))
            return slots[i] if i < len(slots) else ""
        return MARK_RE.sub(replace, text)

    def _translation_for(self, matched):
        for term, translation in self.entries:
            if term == matched:
                return translation
        return matched

    def __len__(self):
        return len(self.entries)


class GlossaryBackend(object):
    """Embrulha um tradutor: protege os termos antes e restaura depois."""

    def __init__(self, inner, glossary):
        self.inner = inner
        self.glossary = glossary
        self.name = inner.name

    def translate_batch(self, lines):
        protected = [self.glossary.protect(line) for line in lines]
        translated = self.inner.translate_batch([p[0] for p in protected])
        out = []
        for (_, slots), text in zip(protected, translated):
            restored = self.glossary.restore(text, slots)
            if MARK_RE.search(restored):
                restored = MARK_RE.sub("", restored)
            out.append(restored)
        return out
