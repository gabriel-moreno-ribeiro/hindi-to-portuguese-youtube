# hindi2pt

Tem muito vídeo bom de tecnologia, culinária e música saindo da Índia em hindi, e a legenda do YouTube só vai até o inglês (quando vai). Eu quero assistir em português. O plano é: baixar a legenda em hindi, traduzir pra pt-BR, gerar um `.srt`.

Por enquanto só a primeira parte: baixa a legenda com o `youtube-dl` e converte de WebVTT pra SRT.

```sh
pip install -e .
hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/
hindi2pt video.hi.vtt          # ou um arquivo que você já tem
```

Testes: `pytest`.
