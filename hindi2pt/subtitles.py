"""Arquivos de legenda: leitura e escrita de SRT e WebVTT, e a limpeza da legenda automatica.

O YouTube entrega a legenda como WebVTT (o ``youtube-dl --sub-format vtt``).
A automatica vem com cada linha repetida no cue seguinte (o "rolling caption",
que rola na tela) e com uma tag de tempo por palavra. ``dedupe_rolling`` tira isso,
``merge_short`` junta os pedacinhos em frases e ``fix_overlaps`` garante que cada
legenda fique na tela tempo suficiente pra ler. Depois de traduzir, ``wrap`` quebra
em duas linhas e ``fit_reading_speed`` estica o que ficou rapido demais pra ler.
"""
import re

TIME_RE = re.compile(r"(\d+):(\d\d):(\d\d)[.,](\d{1,3})")
SHORT_TIME_RE = re.compile(r"(\d\d):(\d\d)[.,](\d{1,3})")  # o VTT aceita mm:ss.mmm
TAG_RE = re.compile(r"<[^>]+>")
DEVANAGARI_DANDA = "।"  # o "ponto final" do hindi; o tradutor se perde com ele


class Cue(object):
    """Uma legenda: quando entra, quando sai e o texto."""

    def __init__(self, start, end, text):
        self.start = float(start)  # segundos
        self.end = float(end)
        self.text = text

    @property
    def duration(self):
        return self.end - self.start

    def copy(self, **changes):
        c = Cue(self.start, self.end, self.text)
        for k, v in changes.items():
            setattr(c, k, v)
        return c

    def __eq__(self, other):
        return isinstance(other, Cue) and (self.start, self.end, self.text) == (other.start, other.end, other.text)

    def __repr__(self):
        return "Cue(%r, %r, %r)" % (self.start, self.end, self.text)


def parse_time(text):
    text = text.strip()
    m = TIME_RE.fullmatch(text)
    if m:
        h, mi, s, ms = m.groups()
        return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000
    m = SHORT_TIME_RE.fullmatch(text)
    if m:
        mi, s, ms = m.groups()
        return int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000
    raise ValueError(f"tempo invalido: {text!r}")


def format_time(seconds, sep=","):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    mi, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{mi:02d}:{s:02d}{sep}{ms:03d}"


def clean_text(text):
    """Tira tags (<i>, <c>, <00:00:01.000>...), entidades e espaco sobrando."""
    text = TAG_RE.sub("", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def parse(content):
    """Le SRT ou WebVTT (descobre pelo conteudo)."""
    content = content.lstrip("﻿")
    lines = content.replace("\r\n", "\n").split("\n")
    cues = []
    i = 0
    is_vtt = lines[0].startswith("WEBVTT") if lines else False
    if is_vtt:
        while i < len(lines) and lines[i].strip():  # pula o cabecalho
            i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or (is_vtt and (line.startswith("NOTE") or line.startswith("STYLE"))):
            i += 1
            if is_vtt and (line.startswith("NOTE") or line.startswith("STYLE")):
                while i < len(lines) and lines[i].strip():
                    i += 1
            continue
        if "-->" not in line:
            # numero do SRT ou identificador de cue do VTT
            i += 1
            if i >= len(lines) or "-->" not in lines[i]:
                continue
            line = lines[i].strip()
        times = line.split("-->")
        start = parse_time(times[0])
        end = parse_time(times[1].strip().split(" ")[0])
        i += 1
        text_lines = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        text = clean_text("\n".join(text_lines))
        if text:
            cues.append(Cue(start, end, text))
    return cues


def to_srt(cues):
    out = []
    for n, cue in enumerate(cues, 1):
        out.append(f"{n}\n{format_time(cue.start)} --> {format_time(cue.end)}\n{cue.text}\n")
    return "\n".join(out)


def to_vtt(cues):
    out = ["WEBVTT\n"]
    for cue in cues:
        out.append(f"{format_time(cue.start, '.')} --> {format_time(cue.end, '.')}\n{cue.text}\n")
    return "\n".join(out)


def dedupe_rolling(cues):
    """A legenda automatica do YouTube repete a linha anterior em cada cue (pra rolar na tela).
    Fica so com o texto que cada cue acrescenta."""
    out = []
    previous_lines = []
    for cue in cues:
        lines = [l for l in cue.text.split("\n") if l.strip()]
        new_lines = [l for l in lines if l not in previous_lines]
        previous_lines = lines
        if not new_lines:
            continue
        out.append(cue.copy(text=" ".join(new_lines)))
    return out


def merge_short(cues, max_chars=84, max_gap=0.7, max_duration=7.0):
    """Junta fragmentos consecutivos em legendas do tamanho de uma frase, parando em
    pontuacao de fim de frase, pausa longa ou quando a legenda ficaria comprida demais."""
    out = []
    for cue in cues:
        if out:
            last = out[-1]
            joined = f"{last.text} {cue.text}"
            ends_sentence = last.text.rstrip().endswith((".", "!", "?", DEVANAGARI_DANDA))
            if (not ends_sentence and cue.start - last.end <= max_gap and len(joined) <= max_chars
                    and cue.end - last.start <= max_duration):
                out[-1] = last.copy(end=max(last.end, cue.end), text=joined)
                continue
        out.append(cue.copy())
    return out


def fix_overlaps(cues, min_duration=0.8):
    """Garante que as legendas nao se sobreponham e que cada uma fique na tela o bastante pra ler."""
    out = [c.copy() for c in cues]
    for k, cue in enumerate(out):
        if k + 1 < len(out) and cue.end > out[k + 1].start:
            cue.end = out[k + 1].start
        if cue.end - cue.start < min_duration:
            limit = out[k + 1].start if k + 1 < len(out) else cue.start + min_duration
            cue.end = max(cue.end, min(cue.start + min_duration, limit))
    return out


def normalize(cues):
    """A limpeza toda que a legenda automatica precisa antes de ir pro tradutor."""
    cues = dedupe_rolling(cues)
    cues = [c.copy(text=c.text.replace(DEVANAGARI_DANDA, ".")) for c in cues]
    cues = merge_short(cues)
    return fix_overlaps(cues)


def wrap(text, width=42):
    """Quebra uma linha traduzida em no maximo duas linhas equilibradas pra tela."""
    text = " ".join(text.split())
    if len(text) <= width:
        return text
    words = text.split(" ")
    best, best_diff = None, None
    for cut in range(1, len(words)):
        a, b = " ".join(words[:cut]), " ".join(words[cut:])
        diff = abs(len(a) - len(b))
        if best is None or diff < best_diff:
            best, best_diff = (a, b), diff
    return "\n".join(best) if best else text


def chars_per_second(cue):
    text = cue.text.replace("\n", " ")
    return len(text) / cue.duration if cue.duration > 0 else float("inf")


def fit_reading_speed(cues, max_cps=20.0, min_gap=0.1):
    """Portugues e mais comprido que hindi: uma legenda que cabia em 1 s pode virar
    60 caracteres. Acima de ``max_cps`` caracteres por segundo, estica o fim ate
    onde a proxima legenda deixa. O que nao couber, paciencia (fica marcado no log)."""
    out = [c.copy() for c in cues]
    too_fast = []
    for k, cue in enumerate(out):
        if chars_per_second(cue) <= max_cps:
            continue
        needed = cue.start + len(cue.text.replace("\n", " ")) / max_cps
        limit = out[k + 1].start - min_gap if k + 1 < len(out) else needed
        cue.end = max(cue.end, min(needed, limit))
        if chars_per_second(cue) > max_cps:
            too_fast.append(k)
    return out, too_fast
