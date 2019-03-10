"""Baixa a legenda de um video do YouTube com o youtube-dl (so a legenda, nao o video),
e lista os videos de uma playlist ou de um canal pra traduzir tudo de uma vez."""
import glob
import json
import os
import re
import subprocess

YOUTUBE_RE = re.compile(r"(youtube\.com/|youtu\.be/)")


def is_url(text):
    return text.startswith("http://") or text.startswith("https://")


def is_playlist(url):
    return "list=" in url or "/channel/" in url or "/user/" in url or "/c/" in url or "/playlist" in url


def video_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{6,})", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)[-24:]


def _run_youtube_dl(cmd, run):
    try:
        result = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise RuntimeError("youtube-dl nao encontrado: pip install youtube-dl")
    if result.returncode != 0:
        raise RuntimeError("youtube-dl falhou: " + result.stderr.decode("utf-8", "replace").strip()[-300:])
    return result


def fetch_subtitles(url, out_dir, lang="hi", log=print, run=subprocess.run):
    """Legenda em hindi: a feita a mao se existir, a automatica se nao. Devolve o caminho do .vtt."""
    os.makedirs(out_dir, exist_ok=True)
    vid = video_id(url)
    cmd = ["youtube-dl", "--skip-download", "--write-sub", "--write-auto-sub", "--sub-lang", lang,
           "--sub-format", "vtt", "-o", os.path.join(out_dir, vid + ".%(ext)s"), url]
    _run_youtube_dl(cmd, run)
    candidates = sorted(glob.glob(os.path.join(out_dir, vid + "*.vtt")))
    if not candidates:
        raise RuntimeError("esse video nao tem legenda em hindi (nem automatica)")
    log(f"legenda: {os.path.basename(candidates[0])}")
    return candidates[0]


def list_videos(url, run=subprocess.run, limit=None):
    """Os videos de uma playlist/canal, do mais antigo pro mais novo, como URLs."""
    cmd = ["youtube-dl", "--flat-playlist", "-j", url]
    if limit:
        cmd[1:1] = ["--playlist-end", str(limit)]
    result = _run_youtube_dl(cmd, run)
    urls = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        vid = entry.get("id") or entry.get("url")
        if vid:
            urls.append(vid if is_url(vid) else "https://www.youtube.com/watch?v=" + vid)
    if not urls:
        raise RuntimeError("nao achei video nenhum nessa playlist")
    return urls
