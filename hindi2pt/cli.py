"""hindi2pt: pega a legenda em hindi de um video do YouTube, traduz pra pt-BR e salva como SRT.

    hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/ -b google --key ...
    hindi2pt video.hi.vtt -b googletrans           # ou um arquivo local, com o tradutor de graca
    hindi2pt video.hi.srt --raw                    # legenda feita a mao: nao precisa de limpeza
"""
import argparse
import os
import re
import sys

from . import subtitles
from .fetch import fetch_subtitles, is_url
from .translate import Translator, make_backend


def translate_file(source, translator, out_dir, log=print, raw=False):
    with open(source, encoding="utf-8") as f:
        cues = subtitles.parse(f.read())
    if not raw:
        before = len(cues)
        cues = subtitles.normalize(cues)
        log(f"limpeza: {before} cues viraram {len(cues)}")
    log(f"{len(cues)} legendas pra traduzir com {translator.backend.name}")
    texts = translator.translate([c.text for c in cues], progress=lambda d, t: log(f"  {d}/{t}"))
    translated = [c.copy(text=t) for c, t in zip(cues, texts)]
    stem = re.sub(r"\.(hi|hi-[\w-]+)$", "", os.path.splitext(os.path.basename(source))[0])
    out = os.path.join(out_dir, stem + ".pt-BR.srt")
    os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(subtitles.to_srt(translated))
    log(f"pronto: {len(translated)} legendas -> {out}")
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="hindi2pt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", help="URL do YouTube ou um arquivo .srt/.vtt")
    p.add_argument("-o", "--out", default="out", help="pasta de saida (padrao: out/)")
    p.add_argument("-b", "--backend", default="googletrans", help="google (com chave), googletrans (de graca) ou dummy")
    p.add_argument("--key", default=os.environ.get("GOOGLE_TRANSLATE_KEY"), help="chave da API do Google Cloud Translation")
    p.add_argument("--batch", type=int, default=40, help="linhas por pedido de traducao")
    p.add_argument("--raw", action="store_true", help="nao limpa a legenda (pra legenda feita a mao)")
    args = p.parse_args(argv)
    try:
        translator = Translator(make_backend(args.backend, args.key), batch_size=args.batch)
        source = fetch_subtitles(args.source, args.out) if is_url(args.source) else args.source
        translate_file(source, translator, args.out, raw=args.raw)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0
