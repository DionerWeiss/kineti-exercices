# Geradores das animações

As animações são Lottie JSON geradas por código, a partir do mesmo rig dos testes clínicos do app (`kineti_app/tool/lottie`: `kineti_lottie.py`, `figure3d.py` e os builders base).

```bash
python3 tool/build_catalog.py            # gera tudo em exercises/<área>/ e clinical_tests/
python3 tool/build_catalog.py bridge     # gera só alguns slugs
python3 tool/build_catalog.py --check    # regenera em memória e compara com o que está commitado
```

- `catalog.json` (raiz) é a fonte única: áreas, testes de referência e exercícios. O painel `index.html` e o `build_catalog.py` leem dele.
- Cada `build_library_*_animations.py` expõe `SCENES = {slug: função}`. Para um exercício novo: escreva a cena, registre em `SCENES`, adicione a entrada em `catalog.json` e rode o build e o `--check`.
- O rig é procurado em `../kineti_app/tool/lottie`. Para usar outro caminho, defina `KINETI_LOTTIE_DIR`.
- `bed_rolling` e `lying_to_sitting` vêm de builders do app sem registro `SCENES` e ficam como arquivos commitados.

Regras de cena: um loop de 5 a 8 s (posição inicial, execução, retorno), marcadores nomeados por etapa, corpo inteiro e apoios dentro do quadro de 720 × 450, sem textos nem setas, e cores só por papel (`figure`, `prop`, `marker`...).
