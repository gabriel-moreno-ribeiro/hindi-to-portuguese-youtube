# hindi2pt

> 🇺🇸 [English version below](#english)

Tem muito vídeo bom de tecnologia, culinária e música saindo da Índia em hindi, e a legenda do YouTube só vai até o inglês (quando vai). Em agosto de 2018 eu quis assistir uma série de receitas de um canal de Delhi e acabei escrevendo isso aqui: pega a legenda em hindi de um vídeo, arruma a bagunça da legenda automática (aquela que repete a linha anterior e quebra palavra por palavra), traduz pra português do Brasil e gera um `.srt`. Se quiser, gera uma dublagem em voz sintética e queima tudo no vídeo com ffmpeg.

Um ano depois virou o que eu uso pra qualquer vídeo em hindi: playlist inteira, glossário pra não traduzir "paneer" como "queijo", e um modo de revisão pra corrigir na mão o que o Google errou.

```sh
pip install -e .[free,dub]
hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/          # googletrans, de graça
hindi2pt video.hi.vtt -b google --key AIza...                     # Google Cloud Translation (melhor, tem cota grátis)
hindi2pt URL --glossary nomes.txt                                 # termos que o tradutor não pode inventar
hindi2pt URL --dub --burn video.mp4                               # voz em pt-BR (gTTS) + legenda queimada no arquivo
hindi2pt "https://www.youtube.com/playlist?list=..." --limit 20   # a playlist inteira
hindi2pt URL --review revisao.tsv                                 # tabela hindi/português pra corrigir no Excel
hindi2pt URL --apply-review revisao.tsv                           # e o SRT final com as correções
```

Sai `saida/<id>.pt-BR.srt`. Abre no VLC junto com o vídeo, ou usa `--burn`.

## O que acontece por dentro

1. `youtube-dl` baixa a legenda (manual em hindi se existir, automática se não) em WebVTT.
2. `subtitles.normalize` faz a limpeza: tira as tags de karaokê, remove as linhas repetidas do "rolling caption", troca o `।` (o ponto final do devanagari) por `.`, junta fragmentos em frases de até ~84 caracteres respeitando pausas, e garante que nenhuma legenda fique menos de 0.8 s na tela nem sobreponha a próxima.
3. Se tiver glossário, cada termo vira um marcador (`⟦3⟧`) que o tradutor não mexe, e volta depois com a tradução que você escolheu.
4. A tradução vai em lotes de 40 linhas, com cache em disco (`.cache.json`, então rodar de novo é de graça) e retry (o googletrans cai bastante).
5. Cada linha traduzida é quebrada em no máximo duas linhas equilibradas, e a legenda que ficou rápida demais pra ler (português é mais comprido que hindi) é esticada até onde a próxima deixa.
6. Com `--dub`, o gTTS fala cada legenda, o ffmpeg acelera a fala que não coube (até 1.6x) e soma tudo numa trilha silenciosa nos tempos certos. `--burn` queima legenda e voz num vídeo novo.

Tradutores: `googletrans` (de graça, sem chave, instável), `google` (a API de verdade, 500 mil caracteres por mês de graça, passa a chave com `--key` ou `GOOGLE_TRANSLATE_KEY`) e `dummy` pra teste. A interface é uma função `translate_batch(lines) -> lines`, então adicionar outro é uma classe de 10 linhas.

Não vou mentir: tradução automática de hindi pra português em 2019 é mediana. O glossário e o modo revisão existem por isso. Pra uma receita dá; pra um filme, revisa.

## Outras coisas

- `--bilingual`: hindi em itálico embaixo do português, pra quem está aprendendo.
- `--offset -1.5` e `--scale 1.0427`: quando a legenda do YouTube não bate com o arquivo de vídeo que você tem (o segundo é 25/23.976).
- `--raw`: legenda feita à mão, sem a limpeza.
- `--max-cps 17`: quantos caracteres por segundo você consegue ler.

## Testes

`pytest`: parser de SRT/VTT (inclusive o formato zoado do YouTube com timestamps por palavra), ida e volta de tempos, dedupe das legendas "rolantes", regras de junção (comprimento, pausa, fim de frase), sobreposição e duração mínima, a quebra em duas linhas, velocidade de leitura, o tradutor com lotes/cache/retry, a API v2 do Google (mockada), o glossário, a dublagem com um ffmpeg de mentira, playlists, deslocamento e escala, o modo revisão e o CLI de ponta a ponta com um arquivo local. Nada de rede nos testes. Roda no Travis em Python 3.6 e 3.7.

---

## English

There's a lot of good tech, cooking and music video coming out of India in Hindi, and YouTube's captions only go as far as English (when they go at all). In August 2018 I wanted to watch a recipe series from a Delhi channel and ended up writing this: it grabs the Hindi captions of a video, cleans up the mess of the automatic captions (the ones that repeat the previous line and break word by word), translates them to Brazilian Portuguese and generates an `.srt`. If you want, it generates a dub with a synthetic voice and burns everything into the video with ffmpeg.

A year later it became what I use for any video in Hindi: whole playlists, a glossary so "paneer" doesn't become "cheese", and a review mode to fix by hand what Google got wrong.

```sh
pip install -e .[free,dub]
hindi2pt "https://www.youtube.com/watch?v=XXXX" -o out/            # googletrans, free
hindi2pt video.hi.vtt -b google --key AIza...                     # Google Cloud Translation (better, has a free quota)
hindi2pt URL --glossary names.txt                                 # terms the translator must not make up
hindi2pt URL --dub --burn video.mp4                               # pt-BR voice (gTTS) + captions burned into the file
hindi2pt "https://www.youtube.com/playlist?list=..." --limit 20   # the whole playlist
hindi2pt URL --review review.tsv                                  # Hindi/Portuguese table to fix in Excel
hindi2pt URL --apply-review review.tsv                            # and the final SRT with the fixes
```

Out comes `out/<id>.pt-BR.srt`. Open it in VLC alongside the video, or use `--burn`.

## What happens inside

1. `youtube-dl` downloads the captions (manual Hindi ones if they exist, automatic if not) as WebVTT.
2. `subtitles.normalize` does the cleanup: strips the karaoke tags, removes the repeated lines of the "rolling caption", swaps the `।` (the Devanagari full stop) for `.`, joins fragments into sentences of up to ~84 characters respecting pauses, and makes sure no caption stays on screen less than 0.8 s or overlaps the next one.
3. With a glossary, every term becomes a marker (`⟦3⟧`) the translator leaves alone, and comes back afterwards with the translation you picked.
4. Translation goes in batches of 40 lines, with a disk cache (`.cache.json`, so running again is free) and retry (googletrans drops a lot).
5. Every translated line is broken into at most two balanced lines, and a caption that got too fast to read (Portuguese is longer than Hindi) is stretched as far as the next one allows.
6. With `--dub`, gTTS speaks every caption, ffmpeg speeds up the speech that didn't fit (up to 1.6x) and mixes everything onto a silent track at the right times. `--burn` burns captions and voice into a new video.

Translators: `googletrans` (free, no key, unstable), `google` (the real API, 500 thousand characters a month for free, pass the key with `--key` or `GOOGLE_TRANSLATE_KEY`) and `dummy` for testing. The interface is a `translate_batch(lines) -> lines` function, so adding another one is a 10-line class.

I won't lie: automatic Hindi to Portuguese translation in 2019 is mediocre. That's why the glossary and the review mode exist. For a recipe it's fine; for a movie, review it.

## Other things

- `--bilingual`: Hindi in italics under the Portuguese, for people who are learning.
- `--offset -1.5` and `--scale 1.0427`: when the YouTube captions don't match the video file you have (the second one is 25/23.976).
- `--raw`: hand-made captions, skip the cleanup.
- `--max-cps 17`: how many characters per second you can read.

## Tests

`pytest`: SRT/VTT parser (including YouTube's messed-up format with per-word timestamps), time round trip, dedupe of the "rolling" captions, joining rules (length, pause, end of sentence), overlap and minimum duration, the two-line break, reading speed, the translator with batches/cache/retry, the Google v2 API (mocked), the glossary, dubbing with a fake ffmpeg, playlists, offset and scale, the review mode and the CLI end to end with a local file. No network in the tests. Runs on Travis with Python 3.6 and 3.7.

MIT.
