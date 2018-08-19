"""Baixa a legenda de um video do YouTube com o youtube-dl (so a legenda, nao o video)."""
import glob
import os
import re
import subprocess

YOUTUBE_RE = re.compile(r"(youtube\.com/|youtu\.be/)")


def is_url(text):
    return text.startswith("http://") or text.startswith("https://")


def video_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{6,})", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)[-24:]


def fetch_subtitles(url, out_dir, lang="hi", log=print, run=subprocess.run):
    """Legenda em hindi: a feita a mao se existir, a automatica se nao. Devolve o caminho do .vtt."""
    os.makedirs(out_dir, exist_ok=True)
    vid = video_id(url)
    cmd = ["youtube-dl", "--skip-download", "--write-sub", "--write-auto-sub", "--sub-lang", lang,
           "--sub-format", "vtt", "-o", os.path.join(out_dir, vid + ".%(ext)s"), url]
    try:
        result = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise RuntimeError("youtube-dl nao encontrado: pip install youtube-dl")
    if result.returncode != 0:
        raise RuntimeError("youtube-dl falhou: " + result.stderr.decode("utf-8", "replace").strip()[-300:])
    candidates = sorted(glob.glob(os.path.join(out_dir, vid + "*.vtt")))
    if not candidates:
        raise RuntimeError("esse video nao tem legenda em hindi (nem automatica)")
    log(f"legenda: {os.path.basename(candidates[0])}")
    return candidates[0]
