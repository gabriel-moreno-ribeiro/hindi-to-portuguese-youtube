# hindi2pt

> 🇺🇸 [English version below](#english)

> **Atualizei em agosto de 2026.** Esse projeto é de 2018 e ficou parado desde 2019. O youtube-dl parou de funcionar, o googletrans morreu de vez, e apareceram coisas bem melhores. O que mudou: o `yt-dlp` no lugar do youtube-dl (o comando antigo continua como fallback), tradução por LLM (`-b openai` ou `-b anthropic`, que dão um português de verdade) e offline com o argos (`-b argos`, agora o padrão), `--audio` pra vídeo sem legenda nenhuma (transcreve com o faster-whisper), as vozes neurais do Edge na dublagem (`--voice edge`; o gTTS de 2019 continua com `--voice gtts`), `pyproject.toml` no lugar do `setup.py` e GitHub Actions no lugar do Travis. Todo o resto (limpeza, glossário, revisão, playlist, bilíngue) é o código de 2018-2019, que continua funcionando igual.

Tem muito vídeo bom de tecnologia, culinária e música saindo da Índia em hindi, e a legenda do YouTube só vai até o inglês (quando vai). Em agosto de 2018 eu quis assistir uma série de receitas de um canal de Delhi e acabei escrevendo isso aqui: pega a legenda em hindi de um vídeo, arruma a bagunça da legenda automática (aquela que repete a linha anterior e quebra palavra por palavra), traduz pra português do Brasil e gera um `.srt`. Se quiser, gera uma dublagem em voz sintética e queima tudo no vídeo com ffmpeg.

Um ano depois virou o que eu uso pra qualquer vídeo em hindi: playlist inteira, glossário pra não traduzir "paneer" como "queijo", e um modo de revisão pra corrigir na mão o que o tradutor errou.

```sh
pip install -e .[offline,dub]
hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/          # argos: offline, sem chave nenhuma
hindi2pt URL -b anthropic                                         # ou openai: tradução muito melhor (ANTHROPIC_API_KEY / OPENAI_API_KEY)
hindi2pt URL --audio                                              # vídeo sem legenda: baixa o áudio e transcreve com whisper
hindi2pt URL --glossary nomes.txt                                 # termos que o tradutor não pode inventar
hindi2pt URL --dub --burn video.mp4                               # voz em pt-BR + legenda queimada no arquivo
hindi2pt "https://www.youtube.com/playlist?list=..." --limit 20   # a playlist inteira
hindi2pt URL --review revisao.tsv                                 # tabela hindi/português pra corrigir no Excel
hindi2pt URL --apply-review revisao.tsv                           # e o SRT final com as correções
hindi2pt video.hi.vtt -b google --key AIza...                     # o jeito de 2018 ainda funciona
```

Sai `saida/<id>.pt-BR.srt`. Abre no VLC junto com o vídeo, ou usa `--burn`.

## O que acontece por dentro

1. `yt-dlp` baixa a legenda (manual em hindi se existir, automática se não) em WebVTT. Sem legenda nenhuma, `--audio` baixa o áudio e o faster-whisper transcreve.
2. `subtitles.normalize` faz a limpeza: tira as tags de karaokê, remove as linhas repetidas do "rolling caption", troca o `।` (o ponto final do devanagari) por `.`, junta fragmentos em frases de até ~84 caracteres respeitando pausas, e garante que nenhuma legenda fique menos de 0.8 s na tela nem sobreponha a próxima.
3. Se tiver glossário, cada termo vira um marcador (`⟦3⟧`) que o tradutor não mexe, e volta depois com a tradução que você escolheu.
4. A tradução vai em lotes de 40 linhas numeradas (um LLM vê o contexto das frases vizinhas), com cache em disco (`.cache.json`, então rodar de novo é de graça) e retry.
5. Cada linha traduzida é quebrada em no máximo duas linhas equilibradas, e a legenda que ficou rápida demais pra ler (português é mais comprido que hindi) é esticada até onde a próxima deixa.
6. Com `--dub`, cada legenda vira uma fala (edge-tts ou gTTS), o ffmpeg acelera a que não coube (até 1.6x) e soma tudo numa trilha silenciosa nos tempos certos. `--burn` queima legenda e voz num vídeo novo.

Tradutores: `argos` (offline), `openai`, `anthropic`, `google` (a API v2 do Google Cloud, com `--key` ou `GOOGLE_TRANSLATE_KEY`), `googletrans` (o de 2018, se ainda funcionar pra você) e `dummy` pra teste. A interface é uma função `translate_batch(lines) -> lines`, então adicionar outro é uma classe de 10 linhas.

Não vou mentir: o argos é mediano. Pra uma legenda que preste use um LLM; cada vídeo de 10 min custa uns centavos. O glossário e o modo revisão continuam valendo pra qualquer um deles.

## Outras coisas

- `--bilingual`: hindi em itálico embaixo do português, pra quem está aprendendo.
- `--offset -1.5` e `--scale 1.0427`: quando a legenda do YouTube não bate com o arquivo de vídeo que você tem (o segundo é 25/23.976).
- `--raw`: legenda feita à mão, sem a limpeza.
- `--max-cps 17`: quantos caracteres por segundo você consegue ler.

## Testes

`pytest`: parser de SRT/VTT (inclusive o formato zoado do YouTube com timestamps por palavra), ida e volta de tempos, dedupe das legendas "rolantes", regras de junção (comprimento, pausa, fim de frase), sobreposição e duração mínima, a quebra em duas linhas, velocidade de leitura, o tradutor com lotes/cache/retry, a API v2 do Google (mockada), o parser das respostas numeradas do LLM, o glossário, a dublagem com um ffmpeg de mentira, playlists pelos dois caminhos (yt-dlp e youtube-dl), deslocamento e escala, o modo revisão e o CLI de ponta a ponta com um arquivo local. Nada de rede nos testes. Rodava no Travis em Python 3.6 e 3.7; hoje roda no GitHub Actions.

---

## English

> **Updated in August 2026.** This project is from 2018 and sat still since 2019. youtube-dl stopped working, googletrans died for good, and much better things showed up. What changed: `yt-dlp` instead of youtube-dl (the old command stays as a fallback), translation by LLM (`-b openai` or `-b anthropic`, which give real Portuguese) and offline with argos (`-b argos`, now the default), `--audio` for videos with no captions at all (transcribes with faster-whisper), the Edge neural voices in the dub (`--voice edge`; the 2019 gTTS stays with `--voice gtts`), `pyproject.toml` instead of `setup.py` and GitHub Actions instead of Travis. Everything else (cleanup, glossary, review, playlist, bilingual) is the 2018-2019 code, which keeps working the same.

There's a lot of good tech, cooking and music video coming out of India in Hindi, and YouTube's captions only go as far as English (when they go at all). In August 2018 I wanted to watch a recipe series from a Delhi channel and ended up writing this: it grabs the Hindi captions of a video, cleans up the mess of the automatic captions (the ones that repeat the previous line and break word by word), translates them to Brazilian Portuguese and generates an `.srt`. If you want, it generates a dub with a synthetic voice and burns everything into the video with ffmpeg.

A year later it became what I use for any video in Hindi: whole playlists, a glossary so "paneer" doesn't become "cheese", and a review mode to fix by hand what the translator got wrong.

```sh
pip install -e .[offline,dub]
hindi2pt "https://www.youtube.com/watch?v=XXXX" -o out/            # argos: offline, no key at all
hindi2pt URL -b anthropic                                         # or openai: much better translation (ANTHROPIC_API_KEY / OPENAI_API_KEY)
hindi2pt URL --audio                                              # video without captions: downloads the audio and transcribes with whisper
hindi2pt URL --glossary names.txt                                 # terms the translator must not make up
hindi2pt URL --dub --burn video.mp4                               # pt-BR voice + captions burned into the file
hindi2pt "https://www.youtube.com/playlist?list=..." --limit 20   # the whole playlist
hindi2pt URL --review review.tsv                                  # Hindi/Portuguese table to fix in Excel
hindi2pt URL --apply-review review.tsv                            # and the final SRT with the fixes
hindi2pt video.hi.vtt -b google --key AIza...                     # the 2018 way still works
```

Out comes `out/<id>.pt-BR.srt`. Open it in VLC alongside the video, or use `--burn`.

## What happens inside

1. `yt-dlp` downloads the captions (manual Hindi ones if they exist, automatic if not) as WebVTT. With no captions at all, `--audio` downloads the audio and faster-whisper transcribes it.
2. `subtitles.normalize` does the cleanup: strips the karaoke tags, removes the repeated lines of the "rolling caption", swaps the `।` (the Devanagari full stop) for `.`, joins fragments into sentences of up to ~84 characters respecting pauses, and makes sure no caption stays on screen less than 0.8 s or overlaps the next one.
3. With a glossary, every term becomes a marker (`⟦3⟧`) the translator leaves alone, and comes back afterwards with the translation you picked.
4. Translation goes in batches of 40 numbered lines (an LLM sees the context of the neighbouring sentences), with a disk cache (`.cache.json`, so running again is free) and retry.
5. Every translated line is broken into at most two balanced lines, and a caption that got too fast to read (Portuguese is longer than Hindi) is stretched as far as the next one allows.
6. With `--dub`, every caption becomes speech (edge-tts or gTTS), ffmpeg speeds up the ones that didn't fit (up to 1.6x) and mixes everything onto a silent track at the right times. `--burn` burns captions and voice into a new video.

Translators: `argos` (offline), `openai`, `anthropic`, `google` (the Google Cloud v2 API, with `--key` or `GOOGLE_TRANSLATE_KEY`), `googletrans` (the 2018 one, if it still works for you) and `dummy` for testing. The interface is a `translate_batch(lines) -> lines` function, so adding another one is a 10-line class.

I won't lie: argos is mediocre. For captions worth anything use an LLM; each 10-minute video costs a few cents. The glossary and the review mode still apply to any of them.

## Other things

- `--bilingual`: Hindi in italics under the Portuguese, for people who are learning.
- `--offset -1.5` and `--scale 1.0427`: when the YouTube captions don't match the video file you have (the second one is 25/23.976).
- `--raw`: hand-made captions, skip the cleanup.
- `--max-cps 17`: how many characters per second you can read.

## Tests

`pytest`: SRT/VTT parser (including YouTube's messed-up format with per-word timestamps), time round trip, dedupe of the "rolling" captions, joining rules (length, pause, end of sentence), overlap and minimum duration, the two-line break, reading speed, the translator with batches/cache/retry, the Google v2 API (mocked), the parser for the LLM's numbered answers, the glossary, dubbing with a fake ffmpeg, playlists through both paths (yt-dlp and youtube-dl), offset and scale, the review mode and the CLI end to end with a local file. No network in the tests. It used to run on Travis with Python 3.6 and 3.7; today it runs on GitHub Actions.

MIT.
