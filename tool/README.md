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
- `bed_rolling` e `lying_to_sitting` são gerados por `build_library_bed_animations.py`, no rig 3D. Esse builder acrescenta a rotação `lean`, usada para passar de deitado de lado para sentado, sem mudar as outras cenas.

Regras de cena: um loop de 5 a 8 s (posição inicial, execução, retorno), marcadores nomeados por etapa, corpo inteiro e apoios dentro do quadro de 720 × 450, sem textos nem setas, e cores só por papel (`figure`, `figure-active`, `prop`, `marker`...).

## Boneco da biblioteca

Os exercícios usam o esqueleto e o movimento do rig, mas o boneco é desenhado por `figure_style.py`: pé com calcanhar, sola e ponta; tronco com volume (pelve, cintura, peito e ombros), que mostra barriga, peito e lombar mudando de forma; pescoço e nariz, para indicar para onde a pessoa está virada; e a parte do corpo que trabalha em `figure-active` (o lado de longe em `figure-active-back`).

- O `_rig` instala o estilo, e o `build_catalog.py` liga o estilo em cada exercício. Os testes clínicos de referência ficam com o boneco do rig, igual ao do app.
- Para escolher o destaque de um exercício, edite `STYLE` em `figure_style.py`: segmentos (`near shin`, `both arm`...) e regiões do tronco (`pelvis`, `abdomen`, `thorax`, `upper_back`, `trunk`). `near` é o lado voltado para a câmera. Sem entrada, o exercício fica sem destaque.
- Faixas elásticas usam `marker`, que tem o mesmo laranja do destaque. Nesses exercícios, destaque só o braço (úmero), para a faixa continuar visível.
- No app, `figure-active` e `figure-active-back` precisam estar mapeados no `ClinicalDemonstrationLottie` (terciária e terciária sobre a superfície). Sem isso, eles mantêm a cor clara gravada no JSON.
- Os close-ups de mão têm desenho próprio e não usam este estilo.
