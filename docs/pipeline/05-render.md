# 05 · Render

## Comandos

Com o ambiente de entrega exportado ([02](02-ambiente.md#variáveis-de-ambiente-mannequinpy-e-render_mannequinpy)):

```bash
python3 tool/mannequin/mannequin.py build <move ids>     # -> $MANNEQUIN_OUT/kineti_sub (e desk_sub)
python3 tool/mannequin/mannequin.py sync <move ids>      # -> actions na lib do avatar
python3 tool/mannequin/mannequin.py qa <job ids>         # só checagens, sem vídeo -> $MANNEQUIN_OUT/qa
SHEET_FRACS=0,0.17,0.33,0.5,0.67,0.83 SHEET_NAME=lote01 python3 tool/mannequin/mannequin.py sheet <job ids>
QA=1 python3 tool/mannequin/mannequin.py render <job ids>   # MP4 + checagens
```

**Sempre passe ids.** Sem ids, `sheet` e `render` processam os 688 jobs.

## Formato do vídeo

- 1920×1080, 30 fps, H.264.
- 0,5 s parado na primeira pose (15 quadros, `tpad`), depois a action repetida até ter pelo menos 2 repetições (filtro `loop` do ffmpeg).
- Quadro do vídeo = 15 + quadro da action − 1. Use essa conta para achar um quadro citado por uma checagem.
- Duração de um job do 3D: ~1 min por job com 2 renders em paralelo (~75 jobs/h).

## Lote completo

```bash
tool/mannequin/ops/batch.sh 03        # render + QA + PP + folha de contato + review_lote_03.csv
```

Ou separado, para manter o GPU ocupado enquanto a CPU faz o pós-processamento (a comparação com o PP leva ~2,5 h por lote e depende só da CPU):

```bash
tool/mannequin/ops/render_part.sh R05
tool/mannequin/ops/post_part.sh R05
```

Para muitos lotes de re-render (`final/lotes/lote_R*.txt`), `ops/rerender_gate.sh 2` pega o próximo lote livre (com trava por `mkdir` em `$KINETI_OPS/claims`), mantém no máximo 2 renders e roda o pós-processamento ao fim de cada um. Registro em `$KINETI_OPS/rerender_run.log` e `lote_<NN>.log`.

## Sincronizar a lib final

Depois de juntar correções no repo:

```bash
cp /mnt/e/mannequin/avatar_man/exercises_final.blend /mnt/e/mannequin/avatar_man/exercises_final_before_<motivo>.blend
python3 tool/mannequin/mannequin.py build $(cat merged_moves.txt; echo) && python3 tool/mannequin/mannequin.py sync $(cat merged_moves.txt; echo)
```

- `merged_moves.txt` não tem quebra de linha no fim. Ao concatenar vários, use `cat f; echo`. Uma junção errada já sincronizou só 2 de 52 movimentos.
- Para reconstruir tudo: `ops/full_build.sh` (todos os movimentos kineti e desk-break → `kineti_sub` → lib final).
- Não sincronize enquanto houver render lendo a lib.

## Montar uma lib do avatar do zero

```bash
cp exercises_kineti_cabelo_v9.blend exercises_final.blend
blender -b exercises_final.blend --python tool/mannequin/prep_avatar_lib.py                 # uma cena, cabelo ligado
blender -b exercises_final.blend --python tool/mannequin/sync_actions.py -- <desk-break exercises.blend>   # 435 actions
ops/full_build.sh                                                                          # movimentos do repo
blender -b exercises_final.blend --python tool/mannequin/add_ref.py -- <desk-break mannequin.blend>        # mannequin_ref oculto
```

O avatar em si vem de `avatar/build_man.py` → `avatar/fit_avatar.py` (estilo `lowpoly`) → `avatar/hair_quiff.py`.

O `lowpoly.py` do git difere do build aprovado de 10/11 (cor do cabelo, tamanho da marca). A versão aprovada só existe como bytecode, guardado em `E:\mannequin\avatar_man\lowpoly_aprovado_20261110.cpython-313.pyc` (fonte de 10/11 14:19, 16.544 bytes). Não o coloque em `__pycache__`: o Python o recompila a partir do `.py` atual e o apaga, e foi assim que a cópia do repo se perdeu. Para usá-lo, copie-o como `lowpoly.pyc` para um diretório separado, sem `lowpoly.py` ao lado, e ponha esse diretório no `sys.path`. A lib pronta com esse visual é `exercises_original_rebuild.blend`, e com o cabelo é `exercises_kineti_cabelo_v9.blend`. **Não reconstrua o avatar sem conferir contra `videos_v9`.**
