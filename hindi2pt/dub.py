"""Dublagem: fala cada legenda com o gTTS (a voz do Google Translate, de graca) e monta
uma trilha de audio com cada fala no tempo certo. O ffmpeg faz o trabalho pesado:
acelera a fala que nao coube no tempo da legenda (atempo), soma tudo numa trilha
silenciosa (adelay + amix) e, se quiser, queima a legenda e a voz no video.

Nao vai ganhar premio. Mas da pra assistir a receita enquanto cozinha, sem ler.
"""
import os
import shutil
import subprocess

from . import subtitles


def ffmpeg_available(which=shutil.which):
    return which("ffmpeg") is not None and which("ffprobe") is not None


def audio_duration(path, run=subprocess.run):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        return float(out.stdout.decode("utf-8").strip())
    except ValueError:
        return 0.0


def speak(text, path):  # pragma: no cover - rede
    from gtts import gTTS
    gTTS(text=text, lang="pt", tld="com.br").save(path)


def fit_clip(src, dst, max_seconds, run=subprocess.run):
    """Se a fala e mais comprida que a legenda, acelera ate 1.6x (mais que isso fica ininteligivel)."""
    duration = audio_duration(src, run)
    factor = duration / max_seconds if max_seconds > 0 and duration > max_seconds else 1.0
    factor = min(factor, 1.6)
    if factor <= 1.02:
        shutil.copyfile(src, dst)
        return 1.0
    run(["ffmpeg", "-y", "-i", src, "-filter:a", f"atempo={factor:.3f}", dst], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return factor


def dub(srt_path, out_path, log=print, speak=speak, run=subprocess.run, which=shutil.which):
    """Gera um .mp3 com a dublagem inteira, alinhada com a legenda."""
    if not ffmpeg_available(which):
        raise RuntimeError("a dublagem precisa do ffmpeg e do ffprobe no PATH")
    with open(srt_path, encoding="utf-8") as f:
        cues = subtitles.parse(f.read())
    if not cues:
        raise RuntimeError("legenda vazia, nada pra dublar")
    work = os.path.splitext(out_path)[0] + "_clips"
    os.makedirs(work, exist_ok=True)
    sped_up = 0
    for i, cue in enumerate(cues):
        raw = os.path.join(work, f"{i:05d}.raw.mp3")
        clip = os.path.join(work, f"{i:05d}.mp3")
        if not os.path.exists(clip):
            if not os.path.exists(raw):
                speak(cue.text.replace("\n", " "), raw)
            gap = (cues[i + 1].start - cue.start) if i + 1 < len(cues) else cue.duration + 2
            if fit_clip(raw, clip, max(gap, 0.5), run) > 1.0:
                sped_up += 1
        if (i + 1) % 25 == 0:
            log(f"  falas: {i + 1}/{len(cues)}")
    total = cues[-1].end + 2
    inputs = ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=24000:cl=mono"]
    filters = []
    for i, cue in enumerate(cues):
        inputs += ["-i", os.path.join(work, f"{i:05d}.mp3")]
        ms = int(cue.start * 1000)
        filters.append(f"[{i + 1}]adelay={ms}|{ms}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(cues)))
    filters.append(f"[0]{mix}amix=inputs={len(cues) + 1}:normalize=0[out]")
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[out]", out_path]
    run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    log(f"dublagem: {out_path} ({len(cues)} falas, {sped_up} aceleradas)")
    return out_path


def burn(video, srt_path, out_path, audio=None, log=print, run=subprocess.run, which=shutil.which):
    """Queima a legenda (e troca o audio pela dublagem, se tiver) num video novo."""
    if not ffmpeg_available(which):
        raise RuntimeError("queimar a legenda precisa do ffmpeg no PATH")
    srt_arg = srt_path.replace("\\", "/").replace(":", "\\:")
    cmd = ["ffmpeg", "-y", "-i", video]
    if audio:
        cmd += ["-i", audio, "-map", "0:v", "-map", "1:a"]
    cmd += ["-vf", f"subtitles='{srt_arg}'", out_path]
    run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    log(f"video com legenda: {out_path}")
    return out_path
