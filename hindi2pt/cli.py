"""hindi2pt: pega a legenda em hindi de um video do YouTube e salva como SRT.

    hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/
    hindi2pt video.hi.vtt                                  # ou um arquivo local
"""
import argparse
import os
import re
import sys

from . import subtitles
from .fetch import fetch_subtitles, is_url


def convert(source, out_dir, log=print):
    with open(source, encoding="utf-8") as f:
        cues = subtitles.parse(f.read())
    stem = re.sub(r"\.(hi|hi-[\w-]+)$", "", os.path.splitext(os.path.basename(source))[0])
    out = os.path.join(out_dir, stem + ".hi.srt")
    os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(subtitles.to_srt(cues))
    log(f"{len(cues)} legendas -> {out}")
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="hindi2pt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", help="URL do YouTube ou um arquivo .srt/.vtt")
    p.add_argument("-o", "--out", default="out", help="pasta de saida (padrao: out/)")
    args = p.parse_args(argv)
    try:
        source = fetch_subtitles(args.source, args.out) if is_url(args.source) else args.source
        convert(source, args.out)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0
