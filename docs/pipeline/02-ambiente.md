# 02 · Ambiente e arquivos

## Máquina

- **Sistema:** WSL2 (Ubuntu 24.04) no Windows. O drive `E:\` aparece como `/mnt/e`. Comandos rodam a partir da raiz do repo.
- **Blender:** o executável do Windows, `/mnt/e/tools/blender-5.3.0/blender.exe`, que pode ser trocado com `KINETI_BLENDER`.
  - Ele recebe caminhos do Windows. `mannequin.py` converte com `wslpath -w`. Em comandos manuais, use `E:\...`, ou copie o script para o E:.
  - `wslpath -w` de um diretório que ainda não existe devolve um caminho relativo, e o Blender acaba gravando em `C:\out`. Crie o diretório antes.
  - Variáveis de ambiente só chegam ao Blender do Windows se forem listadas em `WSLENV` (por exemplo `WSLENV=PLANT_DEBUG:QA_DEBUG`). `mannequin.py` já repassa as que usa.
  - O `look` do Blender MCP falha aqui (o Windows não tem `/tmp`). Para ver uma cena, renderize para `E:\` e leia o PNG por `/mnt/e`.
- **GPU:** uma RTX 3060 Ti. Renders do Blender em paralelo ficam **mais lentos** (fatiamento de tempo do WDDM): 4 renders juntos fazem ~30 jobs/h, contra ~50/h com um só e ~75/h com dois. Use no máximo 2 (`ops/rerender_gate.sh 2`).
- **Python:** o `python3` do sistema não tem numpy. Para scripts com numpy, use `uv run -q --no-project --with numpy python3 …`. Para scripts que leem arquivos de fora, acrescente `-I`.
- **Node:** `tool/puppet2d/node_modules` (lottie-web e playwright-core). O Chromium headless vem de `~/.cache/ms-playwright`.
- **ffmpeg/ffprobe** no WSL. Em loops `while read`, use `-nostdin` ou `< /dev/null`, senão o ffmpeg ou o node consomem o stdin.
- `pgrep -f` encontra o próprio shell que espera. Para achar renders, use `pgrep -x blender.exe` ou `pgrep -fc "mannequin.py render"`.

## Primeira configuração

```bash
python3 tool/mannequin/mannequin.py setup      # clona o desk-break no commit fixado em build/desk-break
```

O clone é necessário para `build`: o construtor importa a biblioteca do desk-break, e os jobs `lib: deskbreak` sem avatar leem a lib original.

## Variáveis de ambiente (`mannequin.py` e `render_mannequin.py`)

| Variável | Uso |
|---|---|
| `MANNEQUIN_AVATAR` | Lib do avatar. Com ela, **todos** os jobs (inclusive desk-break) usam o avatar. Final: `/mnt/e/mannequin/avatar_man/exercises_final.blend` |
| `MANNEQUIN_OUT` | Diretório de trabalho (qa/, stills, sheets, kineti_sub). Final: `/mnt/e/mannequin/avatar_man/final` |
| `MANNEQUIN_VIDEOS` | Pasta dos MP4. Final: `/mnt/e/mannequin/avatar_man/out/videos_final` |
| `MANNEQUIN_RES` | `1920x1080` para entrega (padrão 960x540) |
| `MANNEQUIN_MOVES_DIR` | Pasta com `kineti_moves.json` e `deskbreak_moves.json` (padrão: `tool/mannequin`). Usada pelos diretórios de correção |
| `MANNEQUIN_DROP_FRAMES=1` | Apaga os PNGs depois de montar o vídeo (~400 MB por vídeo em 1080p) |
| `MANNEQUIN_REF_VIDEOS` | Vídeos de comparação de duração (padrão `out/videos_v9`) |
| `MANNEQUIN_PALETTE` | Cor do manequim antigo: `areia` (padrão), `cinza`, `ardosia`, `salvia`, `azul` |
| `QA=1` | No `render`, grava também as checagens (camadas 1 e 2) |
| `EEVEE_SAMPLES=16` | Amostras do Eevee. Medido igual ao padrão (diferença média de 0,1/255) e mais rápido |
| `SHEET_FRACS`, `SHEET_NAME` | Frações do vídeo e nome do `sheet` (padrão `0,0.25,0.5` e `sheet`) |
| `WALKER_H` | Altura das manoplas do andador (0,88 m, ajustada pela nota do cliente) |
| Depuração | `PLANT_DEBUG=1`, `NOPLANT=1`, `NOUNCLIP=1`, `QA_DEBUG=footR`, `KB_DEBUG=<id>`, `KB_KEYS=1`, `BALL_DEBUG=1`, `STILL=<quadro>`, `NORENDER=1` |

Ambiente de entrega, como em `ops/render_part.sh`:

```bash
export MANNEQUIN_AVATAR=/mnt/e/mannequin/avatar_man/exercises_final.blend \
       MANNEQUIN_OUT=/mnt/e/mannequin/avatar_man/final MANNEQUIN_RES=1920x1080 \
       MANNEQUIN_VIDEOS=/mnt/e/mannequin/avatar_man/out/videos_final MANNEQUIN_DROP_FRAMES=1 QA=1 EEVEE_SAMPLES=16
```

## Mapa de arquivos

### Repositório (`tool/`)

| Caminho | O que é |
|---|---|
| `tool/mannequin/jobs.json` | **Fonte da verdade** dos 688 vídeos |
| `tool/mannequin/kineti_moves.json` | Movimentos `kineti-*` (507) |
| `tool/mannequin/deskbreak_moves.json` | Os 159 movimentos do desk-break usados, copiados para cá e editáveis |
| `tool/mannequin/pp_removed.json` | Ids do PP retirados por serem "diferente" (34). Precisam de vídeo próprio |
| `tool/mannequin/texts_pt.json`, `catalog.json` | Textos em português (escritos à mão) e o catálogo gerado |
| `tool/mannequin/library_map.json` | Exercícios da biblioteca Kineti → vídeo que os substitui |
| `tool/mannequin/mannequin.py` | CLI: `setup`, `build`, `sync`, `sheet`, `render`, `qa` |
| `tool/mannequin/kineti_builder.py`, `build_lib.py` | Construtor (fork do desk-break) |
| `tool/mannequin/render_mannequin.py` | Render: props, câmera, grip, Eevee |
| `tool/mannequin/plant_hands.py` | reground, clear_limbs, plant, unclip_arms |
| `tool/mannequin/qa_pose.py`, `motion_qa.py`, `motion_review.py`, `video_qa.py` | QA das camadas 1 e 2 |
| `tool/mannequin/pp_compare.py` | Camada 3: baixa os vídeos do PP e monta o lado a lado |
| `tool/mannequin/review.py`, `contact_sheet.py` | Tabelas de revisão e folhas de contato |
| `tool/mannequin/compare_catalog.py` (+ `.html`) | Catálogo comparativo |
| `tool/mannequin/sync_actions.py`, `add_ref.py`, `prep_avatar_lib.py` | Montagem da lib do avatar |
| `tool/mannequin/avatar/` | Construção do avatar (`build_man.py`, `fit_avatar.py`, `lowpoly.py`, `hair_quiff.py`) |
| `tool/mannequin/ops/` | Scripts de operação (lotes, merges, re-render): veja abaixo |
| `tool/puppet2d/` | Lottie 2D |
| `research/pocketphysio/` | Catálogo do PP (fora do git) |

### `tool/mannequin/ops/`

Scripts usados nas rodadas de 13–15/11. O estado das rodadas (listas e notas) fica em `KINETI_OPS`, que por padrão é `/mnt/e/mannequin/avatar_man/ops`.

| Script | Uso |
|---|---|
| `batch.sh NN` | Render + QA + comparação com o PP + folha de contato + `review_lote_NN.csv` |
| `render_part.sh NN` / `post_part.sh NN` | As duas metades do `batch.sh` (render no GPU, pós-processamento na CPU) |
| `rerender_gate.sh [MAX]` | Pega os `lote_R*.txt` pendentes e mantém no máximo MAX renders |
| `lote_qa.sh NN` | QA sem render na lib de rascunho. Lista os jobs com problema `quebrado` |
| `full_build.sh` | Constrói todos os movimentos e sincroniza na lib final |
| `merge_fix.py NN` | Traz os movimentos e `jobs_change` de `fix/lote_NN` para o repo e atualiza `rerender_ids.txt` |
| `merge_pp.py NN` | Junta a camada 3 em `review_pp.json`. Ids "diferente" saem do `jobs.json` e vão para `pp_removed.json` |
| `merge_visual.py NN` | Junta a camada 4 em `review_notes.json` e refaz os CSVs |
| `final_merge.py` | Junta todas as revisões visuais (as mais recentes ganham), refaz `review.csv` e `pendentes_final.json` |
| `pp.sh <ppid…>` | Texto do PP + mosaico de 8 quadros do vídeo dele |
| `pts.py <job> <pontos>` | Posições das juntas ao longo do movimento (de `qa/<job>.motion.npz`) |
| `blink.py <mp4…>` | Detecta quadros que "piscam" (usado no Lottie) |

### Drive E: (`/mnt/e/mannequin`)

| Caminho | O que é |
|---|---|
| `avatar_man/exercises_final.blend` | **Lib de render.** Não edite durante um render |
| `avatar_man/exercises_final_before_*.blend` | Backups antes de cada sincronização grande |
| `avatar_man/exercises_scratch.blend` | Cópia para testes de QA |
| `avatar_man/exercises_kineti_cabelo_v9.blend` | Avatar v9 aprovado (base da lib final) |
| `avatar_man/final/` | Trabalho: `qa/`, `lotes/`, `validation/`, `pp_review/`, `visual_review/`, `review_notes.json`, `review_pp.json`, `review.csv`, `pendentes_final.json`, `RESUMO_FINAL.md` |
| `avatar_man/fix/lote_*/` | Diretórios isolados de cada rodada de correção (`moves/`, `lib.blend`, `out/`, `report.json`) |
| `avatar_man/fix/plant_test/` | Teste da correção da mão em garra (não aplicada) |
| `avatar_man/out/videos_final/` | **Vídeos 3D finais** |
| `avatar_man/out/videos_v9/` | Vídeos de referência do visual aprovado |
| `avatar_man/out/compare/` | Lado a lado com o PP (`<job>.mp4`, `<job>.png`) |
| `avatar_man/out/contact_lote_*.png` | Folhas de contato por lote |
| `avatar_man/ops/` | Estado das rodadas: `rerender_ids.txt`, `notes_plan.json`, `pendentes_final.txt`, `user_notes_l01.csv`, `extra_fixes.txt` |
| `pocketphysio_ref/<pp id>.mp4` | Vídeos do PP em cache + `status.json` |
| `puppet2d/final/` | Lotties finais (`<job>.json`, `.mp4`, `manifest.json`, `sheet_lote_NN.png`, `move_bugs.txt`) |
| `puppet2d/scripts/split-jump-dinh.json` | Boneco lateral de origem |
| `catalogo/` | Catálogo comparativo (`index.html`, `data.js`) |
| `videos/` | Vídeos antigos do manequim. **Não sobrescrever** |
| `kineti_lib/` | Lib antiga do manequim |
