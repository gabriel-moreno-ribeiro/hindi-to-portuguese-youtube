# hindi2pt

Tem muito vídeo bom de tecnologia, culinária e música saindo da Índia em hindi, e a legenda do YouTube só vai até o inglês (quando vai). Eu quero assistir em português. Isso aqui baixa a legenda em hindi de um vídeo, traduz pra pt-BR e gera um `.srt` que abre no VLC junto com o vídeo.

```sh
pip install -e .[free]
hindi2pt "https://www.youtube.com/watch?v=XXXX" -o saida/          # googletrans, de graça
hindi2pt video.hi.vtt -b google --key AIza...                     # Google Cloud Translation (melhor, tem cota grátis)
```

Sai `saida/<id>.pt-BR.srt`.

Tradutores:

- `googletrans`: a biblioteca não oficial que usa o site do Google Translate. De graça, sem chave, e para de funcionar de vez em quando (aí é só esperar ou trocar de IP).
- `google`: a API de verdade do Google Cloud. Precisa criar um projeto e uma chave, mas os primeiros 500 mil caracteres por mês são de graça, o que dá uns 50 vídeos. Passa com `--key` ou na variável `GOOGLE_TRANSLATE_KEY`.
- `dummy`: não traduz nada, só marca as linhas. Pra testar.

Testes: `pytest`.
