"""hindi2pt: pega a legenda em hindi de um video do YouTube, traduz pra pt-BR e salva como SRT.

    hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/           # argos: offline, sem chave
    hindi2pt URL -b anthropic                      # ou openai: traducao muito melhor, precisa da chave no ambiente
    hindi2pt URL --audio                           # video sem legenda: baixa o audio e transcreve com whisper
    hindi2pt video.hi.vtt -b google --key ...      # ou um arquivo local, com a API do Google (a de 2018)
    hindi2pt video.hi.srt --raw                    # legenda feita a mao: nao precisa de limpeza
    hindi2pt URL --glossary nomes.txt              # termos que o tradutor nao pode inventar
    hindi2pt URL --dub --voice edge                # dublagem (vozes do Edge; --voice gtts e a de 2019)
    hindi2pt URL --dub --burn video.mp4            # queima legenda e voz num video novo
    hindi2pt "https://www.youtube.com/playlist?list=..." --limit 20    # a playlist inteira (ou um canal)
    hindi2pt URL --bilingual --offset -1.5         # hindi embaixo do portugues, tudo 1.5 s mais cedo
    hindi2pt URL --review revisao.tsv              # exporta hindi e portugues lado a lado pra corrigir
    hindi2pt URL --apply-review revisao.tsv        # e gera o SRT final com as correcoes

Tudo que ja foi traduzido fica em saida/.cache.json, entao rodar de novo e de graca.
"""
import argparse
import os
import re
import sys

from . import subtitles
from .dub import VOICES, burn, dub
from .fetch import fetch_subtitles, is_playlist, is_url, list_videos, transcribe
from .glossary import Glossary, GlossaryBackend
from .review import export_tsv, import_tsv
from .translate import BACKENDS, Translator, make_backend


def stem_of(source):
    return re.sub(r"\.(hi|hi-[\w-]+)$", "", os.path.splitext(os.path.basename(source))[0])


def write_srt(cues, out_dir, stem, log):
    out = os.path.join(out_dir, stem + ".pt-BR.srt")
    os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(subtitles.to_srt(cues))
    log(f"pronto: {len(cues)} legendas -> {out}")
    return out


def translate_file(source, translator, out_dir, log=print, raw=False, max_cps=20.0, offset=0.0, factor=1.0,
                   bilingual=False, review=None):
    with open(source, encoding="utf-8") as f:
        cues = subtitles.parse(f.read())
    if not raw:
        before = len(cues)
        cues = subtitles.normalize(cues)
        log(f"limpeza: {before} cues viraram {len(cues)}")
    if factor != 1.0:
        cues = subtitles.scale(cues, factor)
    if offset:
        cues = subtitles.shift(cues, offset)
    log(f"{len(cues)} legendas pra traduzir com {translator.backend.name}")
    texts = translator.translate([c.text for c in cues], progress=lambda d, t: log(f"  {d}/{t}"))
    translated = [c.copy(text=subtitles.wrap(t)) for c, t in zip(cues, texts)]
    translated, too_fast = subtitles.fit_reading_speed(translated, max_cps=max_cps)
    for k in too_fast:
        log(f"  aviso: legenda {k + 1} ({subtitles.format_time(translated[k].start)}) passa rapido demais pra ler")
    if review:
        with open(review, "w", encoding="utf-8") as f:
            f.write(export_tsv(cues, translated))
        log(f"revisao: {review} (corrija a coluna 'portugues' e rode de novo com --apply-review)")
    if bilingual:
        translated = subtitles.bilingual(translated, cues)
    return write_srt(translated, out_dir, stem_of(source), log)


def apply_review(source, review_path, out_dir, log=print):
    with open(review_path, encoding="utf-8") as f:
        cues = import_tsv(f.read())
    log(f"revisao aplicada: {len(cues)} legendas de {review_path}")
    return write_srt(cues, out_dir, stem_of(source), log)


def build_translator(args, log=print):
    backend = make_backend(args.backend, args.key)
    if args.glossary:
        glossary = Glossary.load(args.glossary)
        log(f"glossario: {len(glossary)} termo(s)")
        backend = GlossaryBackend(backend, glossary)
    cache = None if args.no_cache else os.path.join(args.out, ".cache.json")
    return Translator(backend, cache, batch_size=args.batch)


def run_one(source, args, translator, log=print):
    if is_url(source):
        path = transcribe(source, args.out, log=log) if args.audio else fetch_subtitles(source, args.out, log=log)
    else:
        path = source
    if args.apply_review:
        srt = apply_review(path, args.apply_review, args.out, log=log)
    else:
        srt = translate_file(path, translator, args.out, log=log, raw=args.raw, max_cps=args.max_cps,
                             offset=args.offset, factor=args.scale, bilingual=args.bilingual, review=args.review)
    audio = None
    if args.dub:
        audio = dub(srt, os.path.join(args.out, stem_of(path) + ".pt-BR.mp3"), log=log, speak=VOICES[args.voice])
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
    p.add_argument("-b", "--backend", default="argos", help=", ".join(BACKENDS))
    p.add_argument("--key", default=os.environ.get("GOOGLE_TRANSLATE_KEY"), help="chave da API do Google Cloud Translation (-b google)")
    p.add_argument("--audio", action="store_true", help="sem legenda? baixa o audio e transcreve com o whisper")
    p.add_argument("--glossary", help="arquivo com 'termo = traducao' por linha")
    p.add_argument("--batch", type=int, default=40, help="linhas por pedido de traducao")
    p.add_argument("--raw", action="store_true", help="nao limpa a legenda (pra legenda feita a mao)")
    p.add_argument("--no-cache", action="store_true", help="ignora o .cache.json")
    p.add_argument("--max-cps", type=float, default=20, help="caracteres por segundo que da pra ler (padrao 20)")
    p.add_argument("--offset", type=float, default=0.0, help="desloca a legenda em segundos (negativo = adianta)")
    p.add_argument("--scale", type=float, default=1.0, help="multiplica os tempos (25/23.976 = 1.0427, por exemplo)")
    p.add_argument("--bilingual", action="store_true", help="hindi em italico embaixo do portugues")
    p.add_argument("--review", metavar="TSV", help="exporta uma tabela hindi/portugues pra revisar")
    p.add_argument("--apply-review", metavar="TSV", help="gera o SRT a partir da tabela revisada (nao traduz de novo)")
    p.add_argument("--dub", action="store_true", help="gera tambem a dublagem em pt-BR")
    p.add_argument("--voice", default="edge", choices=sorted(VOICES), help="voz da dublagem: edge (2026) ou gtts (2019)")
    p.add_argument("--burn", metavar="VIDEO", help="queima a legenda (e a dublagem) nesse arquivo de video")
    p.add_argument("--limit", type=int, help="numa playlist, so os N primeiros videos")
    args = p.parse_args(argv)
    try:
        run(args)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0
