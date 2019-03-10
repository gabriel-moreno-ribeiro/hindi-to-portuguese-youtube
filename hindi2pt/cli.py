"""hindi2pt: pega a legenda em hindi de um video do YouTube, traduz pra pt-BR e salva como SRT.

    hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/ -b google --key ...
    hindi2pt video.hi.vtt -b googletrans           # ou um arquivo local, com o tradutor de graca
    hindi2pt video.hi.srt --raw                    # legenda feita a mao: nao precisa de limpeza
    hindi2pt URL --glossary nomes.txt              # termos que o tradutor nao pode inventar
    hindi2pt URL --dub                             # e uma dublagem em voz sintetica (gTTS + ffmpeg)
    hindi2pt URL --dub --burn video.mp4            # queima legenda e voz num video novo
    hindi2pt "https://www.youtube.com/playlist?list=..." --limit 20    # a playlist inteira (ou um canal)

Tudo que ja foi traduzido fica em saida/.cache.json, entao rodar de novo e de graca.
"""
import argparse
import os
import re
import sys

from . import subtitles
from .dub import burn, dub
from .fetch import fetch_subtitles, is_playlist, is_url, list_videos
from .glossary import Glossary, GlossaryBackend
from .translate import Translator, make_backend


def stem_of(source):
    return re.sub(r"\.(hi|hi-[\w-]+)$", "", os.path.splitext(os.path.basename(source))[0])


def translate_file(source, translator, out_dir, log=print, raw=False, max_cps=20.0):
    with open(source, encoding="utf-8") as f:
        cues = subtitles.parse(f.read())
    if not raw:
        before = len(cues)
        cues = subtitles.normalize(cues)
        log(f"limpeza: {before} cues viraram {len(cues)}")
    log(f"{len(cues)} legendas pra traduzir com {translator.backend.name}")
    texts = translator.translate([c.text for c in cues], progress=lambda d, t: log(f"  {d}/{t}"))
    translated = [c.copy(text=subtitles.wrap(t)) for c, t in zip(cues, texts)]
    translated, too_fast = subtitles.fit_reading_speed(translated, max_cps=max_cps)
    for k in too_fast:
        log(f"  aviso: legenda {k + 1} ({subtitles.format_time(translated[k].start)}) passa rapido demais pra ler")
    out = os.path.join(out_dir, stem_of(source) + ".pt-BR.srt")
    os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(subtitles.to_srt(translated))
    log(f"pronto: {len(translated)} legendas -> {out}")
    return out


def build_translator(args, log=print):
    backend = make_backend(args.backend, args.key)
    if args.glossary:
        glossary = Glossary.load(args.glossary)
        log(f"glossario: {len(glossary)} termo(s)")
        backend = GlossaryBackend(backend, glossary)
    cache = None if args.no_cache else os.path.join(args.out, ".cache.json")
    return Translator(backend, cache, batch_size=args.batch)


def run_one(source, args, translator, log=print):
    path = fetch_subtitles(source, args.out, log=log) if is_url(source) else source
    srt = translate_file(path, translator, args.out, log=log, raw=args.raw, max_cps=args.max_cps)
    audio = None
    if args.dub:
        audio = dub(srt, os.path.join(args.out, stem_of(path) + ".pt-BR.mp3"), log=log)
    if args.burn:
        burn(args.burn, srt, os.path.join(args.out, stem_of(path) + ".pt-BR.mp4"), audio, log=log)
    return srt


def run(args, log=print):
    translator = build_translator(args, log)
    if is_url(args.source) and is_playlist(args.source):
        videos = list_videos(args.source, limit=args.limit)
        log(f"playlist: {len(videos)} video(s)")
        done, failed = [], []
        for n, url in enumerate(videos, 1):
            log(f"[{n}/{len(videos)}] {url}")
            try:
                done.append(run_one(url, args, translator, log))
            except (RuntimeError, ValueError, OSError) as e:
                log(f"  pulei: {e}")
                failed.append(url)
        log(f"playlist: {len(done)} traduzido(s), {len(failed)} pulado(s)")
        if not done:
            raise RuntimeError("nenhum video da playlist deu certo")
        return done
    return [run_one(args.source, args, translator, log)]


def main(argv=None):
    p = argparse.ArgumentParser(prog="hindi2pt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", help="URL do YouTube (video, playlist ou canal) ou um arquivo .srt/.vtt")
    p.add_argument("-o", "--out", default="out", help="pasta de saida (padrao: out/)")
    p.add_argument("-b", "--backend", default="googletrans", help="google (com chave), googletrans (de graca) ou dummy")
    p.add_argument("--key", default=os.environ.get("GOOGLE_TRANSLATE_KEY"), help="chave da API do Google Cloud Translation")
    p.add_argument("--glossary", help="arquivo com 'termo = traducao' por linha")
    p.add_argument("--batch", type=int, default=40, help="linhas por pedido de traducao")
    p.add_argument("--raw", action="store_true", help="nao limpa a legenda (pra legenda feita a mao)")
    p.add_argument("--no-cache", action="store_true", help="ignora o .cache.json")
    p.add_argument("--max-cps", type=float, default=20, help="caracteres por segundo que da pra ler (padrao 20)")
    p.add_argument("--dub", action="store_true", help="gera tambem a dublagem em pt-BR (gTTS + ffmpeg)")
    p.add_argument("--burn", metavar="VIDEO", help="queima a legenda (e a dublagem) nesse arquivo de video")
    p.add_argument("--limit", type=int, help="numa playlist, so os N primeiros videos")
    args = p.parse_args(argv)
    try:
        run(args)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0
