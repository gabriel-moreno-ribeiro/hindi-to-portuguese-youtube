"""Baixa a legenda de um video do YouTube (so a legenda, nao o video) e lista os videos de
uma playlist ou de um canal pra traduzir tudo de uma vez.

Em 2018 isso era o youtube-dl por linha de comando. Em 2026 o youtube-dl praticamente
parou de funcionar e o yt-dlp (um fork) e o que todo mundo usa; se ele estiver instalado
a gente usa a biblioteca dele direto, senao cai no comando antigo. ``transcribe`` e novo:
pra video sem legenda nenhuma, baixa o audio e transcreve com o faster-whisper.
"""
import glob
import json
import os
import re
import subprocess

YOUTUBE_RE = re.compile(r"(youtube\.com/|youtu\.be/)")


def is_url(text):
    return text.startswith("http://") or text.startswith("https://")


def is_playlist(url):
    return "list=" in url or "/channel/" in url or "/user/" in url or "/c/" in url or "/playlist" in url or "/@" in url


def video_id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{6,})", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)[-24:]


def _ytdlp():
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        return None


def _run_youtube_dl(cmd, run):
    try:
        result = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise RuntimeError("nem yt-dlp nem youtube-dl encontrados: pip install yt-dlp")
    if result.returncode != 0:
        raise RuntimeError("youtube-dl falhou: " + result.stderr.decode("utf-8", "replace").strip()[-300:])
    return result


def fetch_subtitles(url, out_dir, lang="hi", log=print, run=subprocess.run, ytdlp=_ytdlp):
    """Legenda em hindi: a feita a mao se existir, a automatica se nao. Devolve o caminho do .vtt."""
    os.makedirs(out_dir, exist_ok=True)
    vid = video_id(url)
    template = os.path.join(out_dir, vid + ".%(ext)s")
    module = ytdlp()
    if module is not None:  # pragma: no cover - rede
        opts = {"skip_download": True, "writesubtitles": True, "writeautomaticsub": True,
                "subtitleslangs": [lang, f"{lang}-*"], "subtitlesformat": "vtt", "outtmpl": template,
                "quiet": True, "no_warnings": True}
        try:
            with module.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
        except Exception as e:
            raise RuntimeError(f"yt-dlp falhou: {str(e)[-300:]}")
    else:
        cmd = ["youtube-dl", "--skip-download", "--write-sub", "--write-auto-sub", "--sub-lang", lang,
               "--sub-format", "vtt", "-o", template, url]
        _run_youtube_dl(cmd, run)
    candidates = sorted(glob.glob(os.path.join(out_dir, vid + "*.vtt")))
    if not candidates:
        raise RuntimeError("esse video nao tem legenda em hindi (nem automatica); tente --audio")
    log(f"legenda: {os.path.basename(candidates[0])}")
    return candidates[0]


def list_videos(url, run=subprocess.run, limit=None, ytdlp=_ytdlp):
    """Os videos de uma playlist/canal, do mais antigo pro mais novo, como URLs."""
    module = ytdlp()
    entries = []
    if module is not None:  # pragma: no cover - rede
        opts = {"extract_flat": True, "quiet": True, "no_warnings": True}
        if limit:
            opts["playlistend"] = limit
        with module.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = [e for e in (info.get("entries") or []) if e]
    else:
        cmd = ["youtube-dl", "--flat-playlist", "-j", url]
        if limit:
            cmd[1:1] = ["--playlist-end", str(limit)]
        result = _run_youtube_dl(cmd, run)
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    urls = []
    for entry in entries:
        vid = entry.get("id") or entry.get("url")
        if vid:
            urls.append(vid if is_url(vid) else "https://www.youtube.com/watch?v=" + vid)
    if not urls:
        raise RuntimeError("nao achei video nenhum nessa playlist")
    return urls


def transcribe(url, out_dir, log=print, model_size="small"):  # pragma: no cover - pesado
    """Video sem legenda: baixa o audio com o yt-dlp e transcreve com o faster-whisper."""
    from . import subtitles

    module = _ytdlp()
    if module is None:
        raise RuntimeError("pip install yt-dlp pra baixar o audio")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("pip install faster-whisper (e o ffmpeg) pra transcrever video sem legenda")
    os.makedirs(out_dir, exist_ok=True)
    vid = video_id(url)
    audio = os.path.join(out_dir, vid + ".m4a")
    with module.YoutubeDL({"format": "bestaudio[ext=m4a]/bestaudio", "outtmpl": audio, "quiet": True}) as ydl:
        ydl.download([url])
    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(audio, language="hi", vad_filter=True)
    cues = [subtitles.Cue(s.start, s.end, s.text.strip()) for s in segments if s.text.strip()]
    path = os.path.join(out_dir, vid + ".hi.srt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(subtitles.to_srt(cues))
    log(f"transcrito: {len(cues)} trechos")
    return path
