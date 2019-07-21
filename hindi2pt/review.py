"""Modo revisao: exporta uma tabela com o hindi e o portugues lado a lado (TSV, abre no
Excel ou no LibreOffice), voce corrige o que o tradutor errou, e importa de volta pra
virar o SRT final. E o unico jeito de uma legenda automatica ficar realmente boa.

Colunas: numero, inicio, fim, hindi, portugues. So a coluna do portugues e lida na volta
(e os tempos, se voce mexer neles).
"""
from . import subtitles

HEADER = ["n", "inicio", "fim", "hindi", "portugues"]


def _cell(text):
    return text.replace("\t", " ").replace("\n", " / ")


def export_tsv(original, translated):
    """Uma linha por legenda. Quebras de linha viram ' / ' pra caber numa celula."""
    rows = ["\t".join(HEADER)]
    for n, (hi, pt) in enumerate(zip(original, translated), 1):
        rows.append("\t".join([str(n), subtitles.format_time(pt.start), subtitles.format_time(pt.end), _cell(hi.text), _cell(pt.text)]))
    return "\n".join(rows) + "\n"


def import_tsv(text, width=42):
    """Le a tabela de volta. Linhas vazias e a de cabecalho sao ignoradas; ' / ' vira quebra de linha."""
    cues = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        cols = raw.rstrip("\n").split("\t")
        if cols[0].strip().lower() == HEADER[0]:
            continue
        if len(cols) < 5:
            raise ValueError(f"linha com menos de 5 colunas: {raw[:60]!r}")
        pt = cols[4].strip()
        if not pt:
            continue   # linha apagada de proposito
        pt = "\n".join(part.strip() for part in pt.split(" / ")) if " / " in pt else subtitles.wrap(pt, width)
        cues.append(subtitles.Cue(subtitles.parse_time(cols[1]), subtitles.parse_time(cols[2]), pt))
    if not cues:
        raise ValueError("a tabela nao tem nenhuma legenda")
    return cues
