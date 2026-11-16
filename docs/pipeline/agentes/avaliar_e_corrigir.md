# Prompt: avaliar exercícios e criar uma versão nova

Prompt completo para um agente coordenador. Ele avalia **todos** os vídeos de exercícios contra o PocketPhysio, corrige o que precisar e gera uma **versão nova completa em diretórios separados**, sem tocar na entrega atual. Os campos da seção **Tarefa** já estão preenchidos para a rodada v10. Para outra rodada, troque o nome e os caminhos.

---

Você é o coordenador de uma rodada de revisão dos vídeos de exercícios animados do Kineti (avatar 3D low-poly, feito no Blender). A referência clínica é o vídeo do PocketPhysio (PP). Avalie os 688 vídeos, corrija os que estiverem errados e produza uma versão nova completa num diretório próprio.

A entrega atual **não pode mudar**: repo principal, lib de render, vídeos, revisões e catálogo ficam como estão. Trabalhe de forma autônoma e só pare nos pontos marcados com **PARE**.

## Tarefa

- **Escopo:** todos os jobs de `tool/mannequin/jobs.json` (688).
- **Até onde ir:** avaliar, corrigir e renderizar uma versão nova em diretórios novos. **Não** aplicar na entrega.
- **Nome da versão:** `v10`.

| Nome | Caminho | O que é |
|---|---|---|
| `MAIN` | `/home/dioner/projects/kineti/animated_exercices` | Repo principal. Só leitura |
| `WT` | `/home/dioner/projects/kineti/animated_exercices_v10` | Git worktree da versão nova, no branch `revisao-v10`. Todas as edições de código e dados vão aqui |
| `V` | `/mnt/e/mannequin/avatar_man/v10` | Dados da versão nova: lib, QA, revisões, correções e vídeos |

## Leia antes de começar

Documentação em `$MAIN/docs/pipeline/` (a mesma existe em `$WT/docs/pipeline/`). Leia nesta ordem:

1. `README.md`: regras gerais e glossário (job, move, lib, irmãos, ok/corrigido/pendente).
2. `02-ambiente.md`: máquina, variáveis de ambiente e mapa de arquivos.
3. `03-movimentos.md`: formato dos moves, convenção de sinais, o que o construtor faz, receitas que funcionaram.
4. `06-revisao.md`: as quatro camadas de QA e os limiares.
5. `07-pocketphysio.md`: como comparar com o PP.
6. `08-correcao.md`: diretório isolado, formato do `report.json`, merge e notas do cliente.
7. `12-limites-e-decisoes.md`: decisões do dono do projeto, pendências abertas e tentativas já revertidas. **Não repita o que já falhou.**
8. Conforme a necessidade: `04-camera-e-props.md`, `05-render.md`, `09-lottie.md`.

Instruções já testadas para cada etapa (em inglês), em `docs/pipeline/agentes/`:

- `validation_brief.md`: avaliação por job, no estilo do cliente.
- `fix_brief.md`: correção. Tem setup, comandos, formato do move, sinais e truques.
- `client_round_brief.md`: como tratar notas do cliente e irmãos.
- `layer4R_brief.md`: revisão visual depois do re-render.

Esses briefs foram escritos para a entrega atual. Nesta rodada, troque os caminhos assim:

| Onde o brief diz | Use |
|---|---|
| `/home/dioner/projects/kineti/animated_exercices` | `$WT` |
| `/mnt/e/mannequin/avatar_man/exercises_final.blend` | `$V/lib.blend` |
| `/mnt/e/mannequin/avatar_man/fix/` | `$V/fix/` |
| `/mnt/e/mannequin/avatar_man/final/` | `$V/final/` |
| `/mnt/e/mannequin/avatar_man/out/videos_final/` | `$V/videos/` |

## Ambiente

- WSL2 no Windows. O drive `E:\` está em `/mnt/e`.
- Blender do Windows: `/mnt/e/tools/blender-5.3.0/blender.exe`.
  - O `mannequin.py` converte os caminhos para o formato do Windows.
  - Crie os diretórios de saída antes de usar: um diretório inexistente vira `C:\out`.
  - O `look` do Blender MCP **não funciona** aqui. Para ver uma cena, renderize para `E:\` e leia o PNG por `/mnt/e/...`.
- Python com numpy: `uv run -q --no-project --with numpy python3 …`. O `python3` do sistema não tem numpy.
- GPU (RTX 3060 Ti): **no máximo 2 renders do Blender ao mesmo tempo**, porque mais que isso fica mais lento.
  - Antes de renderizar, rode `pgrep -x blender.exe | wc -l`.
  - QA e stills também abrem o Blender. Por isso, no máximo 3 agentes de lote trabalham ao mesmo tempo.
- ffmpeg dentro de loops `while read`: use `-nostdin`.
- Os scripts de `tool/mannequin/ops/` leem os caminhos das variáveis `KINETI_*` (`ops/env.sh` e `ops/kpaths.py`). O repo que eles usam é o que contém o script. Por isso, rode sempre os scripts de `$WT`, com o `$V/env.sh` carregado.

## Arquivos

**Código e dados (em `$WT`, cópia do repo principal):**

| Caminho | O que é |
|---|---|
| `tool/mannequin/jobs.json` | Os 688 vídeos: `lib`, `view`, `props`, `pocketphysio` (ids do PP), `move`, `frame` |
| `tool/mannequin/kineti_moves.json` | Moves `kineti-*` (507) |
| `tool/mannequin/deskbreak_moves.json` | Moves do desk-break usados (159) |
| `tool/mannequin/catalog.json`, `texts_pt.json` | Nomes e textos em português |
| `tool/mannequin/pp_removed.json` | Ids do PP retirados por serem outro movimento |
| `tool/mannequin/mannequin.py` | CLI: `build`, `sync`, `qa`, `sheet`, `render` |
| `tool/mannequin/kineti_builder.py`, `plant_hands.py`, `render_mannequin.py` | Construtor, apoio das mãos e render |
| `tool/mannequin/motion_review.py`, `video_qa.py`, `pp_compare.py` | QA das camadas 2 e 3 |
| `tool/mannequin/ops/` | `merge_fix.py`, `render_part.sh`, `post_part.sh`, `rerender_gate.sh`, `final_merge.py`, `pp.sh`, `pts.py` |
| `research/pocketphysio/exercicios.json` | Catálogo do PP: nome, descrição e posição de cada id |

**Blender:**

| Caminho | O que é |
|---|---|
| `$V/lib.blend` | Lib de render da v10 (cópia da lib final no setup) |
| `$V/fix/lote_NN/lib.blend` | Lib de trabalho de cada agente de lote |
| `/mnt/e/mannequin/avatar_man/exercises_final.blend` | Lib da entrega atual. **Só leitura**: copie uma vez no setup e não abra de novo |
| `/mnt/e/mannequin/avatar_man/exercises_kineti_cabelo_v9.blend` | Avatar v9 aprovado. Não mexa |

**Referências (só leitura):**

| Caminho | O que é |
|---|---|
| `/mnt/e/mannequin/avatar_man/out/videos_final/<job>.mp4` | Vídeos da entrega atual (versão anterior à v10) |
| `/mnt/e/mannequin/avatar_man/out/videos_v9/` | Referência do visual aprovado |
| `/mnt/e/mannequin/avatar_man/out/compare/<job>.png` e `.mp4` | Lado a lado da entrega atual com o PP (início, pico, retorno) |
| `/mnt/e/mannequin/pocketphysio_ref/<pp id>.mp4` + `status.json` | Vídeos do PP em cache. O `pp_compare.py fetch` pode acrescentar arquivos aqui |
| `/mnt/e/mannequin/avatar_man/final/review.csv`, `pendentes_final.json`, `RESUMO_FINAL.md` | Veredito atual de cada job e as 33 pendências |
| `/mnt/e/mannequin/avatar_man/fix/lote_*/report.json` | Todas as correções anteriores (C1–C3 e R2a–R4a são as mais novas) |
| `/mnt/e/mannequin/avatar_man/ops/user_notes_l01.csv` | As 32 notas do cliente no lote 01, já aplicadas. Mostram o nível de exigência |
| `/mnt/e/mannequin/videos/` | Vídeos antigos do manequim. **Nunca sobrescreva** |

## Regras invioláveis

1. O **vídeo** do PP é a verdade: posição inicial, amplitude, braços, contatos, lado e ritmo. O texto e a versão anterior valem menos.
2. Corrija na fonte: no move (`*_moves.json`), em `jobs_change` (vista, props) ou, se for indispensável, no construtor ou no `plant_hands` dentro de `$WT`. Nunca edite o MP4.
3. **Sem suavização global** para esconder trancos: ela solta os contatos.
4. **Não mude a aparência do avatar** (corpo, malha, roupa, cabelo). Se uma correção parecer pedir isso, resolva pela pose ou explique no `motivo`.
5. **Sem Gemini nem Vertex.** Pergunte antes de usar qualquer outro modelo externo pago. Você e os seus agentes olham as imagens.
6. **Não aplique a correção da mão em garra** (`fix/plant_test`). Ela foi testada e recusada em 15/11.
7. Decisões que não se revertem:
   - ponte unipodal **sem ponte**;
   - pausas de ~2 s no pico;
   - tranco máximo de 12°/quadro em caminhadas e avanços e de 8°/quadro nos demais.
8. Nunca rode `sheet`, `render` ou `rebuild` sem lista de ids: sem ids, o comando processa os 688.
9. **Não grave em nada da entrega atual:**
   - em `$MAIN`, nem nos arquivos, nem no git, nem no branch `main`;
   - em `/mnt/e/mannequin/avatar_man/{exercises_final.blend, final/, fix/, ops/, out/}`;
   - em `/mnt/e/mannequin/{videos, catalogo, puppet2d}`.

   Se um comando for gravar fora de `$WT` e `$V`, pare e confira as variáveis. A única exceção é o cache `pocketphysio_ref`.
10. Não faça commit nem push, não rode `compare_catalog.py`, `sync-catalog.mjs` nem `upload-catalog.mjs` e não envie nada para o R2 ou o Supabase.

## Fase 0 · Preparar (coordenador)

```bash
MAIN=/home/dioner/projects/kineti/animated_exercices
WT=/home/dioner/projects/kineti/animated_exercices_v10
V=/mnt/e/mannequin/avatar_man/v10
test ! -e $WT && test ! -e $V || { echo "já existe: pare e pergunte"; exit 1; }
pgrep -x blender.exe && echo "render rodando: espere antes de copiar a lib"

# código: worktree num branch novo
git -C $MAIN worktree add -b revisao-v10 $WT
# se as mudanças de ops/ ainda não estiverem commitadas no MAIN, traga-as
[ -f $WT/tool/mannequin/ops/env.sh ] || cp -r $MAIN/tool/mannequin/ops/. $WT/tool/mannequin/ops/
git -C $MAIN diff --quiet HEAD -- tool/mannequin || echo "ATENÇÃO: MAIN tem mudanças não commitadas em tool/mannequin; compare antes de seguir"
mkdir -p $WT/build && cp -r $MAIN/build/desk-break $WT/build/   # build/ fica fora do git; cópia (42 MB), não link: o Blender do Windows pode não seguir links do WSL

# dados
mkdir -p $V/{final/lotes,final/validation,final/visual_review,out/compare,videos,fix,ops}
cp /mnt/e/mannequin/avatar_man/exercises_final.blend $V/lib.blend
cp -r /mnt/e/mannequin/avatar_man/final/{qa,kineti_sub,review_notes.json,review_pp.json} $V/final/
cp /mnt/e/mannequin/avatar_man/out/videos_final/*.mp4 $V/videos/      # a v10 começa igual à entrega atual
: > $V/ops/rerender_ids.txt

cat > $V/env.sh <<EOF
export KINETI_FINAL=$V/final KINETI_OUT=$V/out KINETI_LIB=$V/lib.blend KINETI_VIDEOS=$V/videos \\
       KINETI_FIX=$V/fix KINETI_OPS=$V/ops KINETI_QA_LIB=$V/lib.blend
export MANNEQUIN_REF_VIDEOS=/mnt/e/mannequin/avatar_man/out/videos_v9 PP_COMPARE=$V/out/compare
cd $WT
EOF
```

Depois:

1. **Lotes.** Os lotes antigos não batem mais com o `jobs.json`. Gere `$V/final/lotes/lote_01.txt` … `lote_14.txt` com os ids do `jobs.json` em ordem alfabética, ~50 por arquivo, separados por espaço. A ordem alfabética junta as famílias (`kineti-bed-*`, `kineti-chair-*`…), o que ajuda a achar os irmãos. Grave também `$V/final/all_ids.txt` com todos os ids.
2. **Dono de cada move.** Vários jobs compartilham um move, às vezes em lotes diferentes. Grave `$V/ops/move_owner.json` (`{move: "NN"}`) com o lote do primeiro job que usa cada move. O move de um job é `jobs.json[job].move` ou, se não houver, o próprio id. **Só o lote dono edita o move.**
3. **Contexto por job.** Grave `$V/ops/contexto.json` com, para cada job:
   - o veredito e a nota atuais (`final/review.csv`);
   - a pendência, se houver (`pendentes_final.json`);
   - as correções anteriores (todos os `fix/lote_*/report.json`).

   Os agentes de lote leem esse arquivo para não repetir tentativas que falharam.
4. Crie `$V/ops/progresso.md`. Atualize-o a cada lote, para poder retomar se o trabalho for interrompido.

## Fase 1 e 2 · Avaliar e corrigir (um agente por lote)

Dispare um agente por lote, **no máximo 3 ao mesmo tempo**. Cada agente recebe:

- o número do lote (`NN`);
- os caminhos `$WT` e `$V`;
- as seções **Regras invioláveis** e **Ambiente** deste prompt;
- as instruções abaixo.

O agente faz a avaliação e a correção do mesmo lote, nessa ordem.

### Setup do lote

```bash
source /mnt/e/mannequin/avatar_man/v10/env.sh
W=$V/fix/lote_NN
mkdir -p $W/out $W/moves
cp $WT/tool/mannequin/{kineti_moves,deskbreak_moves}.json $W/moves/
cp $V/lib.blend $W/lib.blend
export MANNEQUIN_MOVES_DIR=$W/moves MANNEQUIN_OUT=$W/out MANNEQUIN_AVATAR=$W/lib.blend MANNEQUIN_RES=1920x1080
```

Antes de editar, rode o QA de todos os jobs do lote e guarde o resultado em `$W/qa_before/`:

- camada 1: `python3 tool/mannequin/mannequin.py qa <ids>`;
- camada 2: `motion_review.py` (ver `fix_brief.md`).

### Avaliar

Siga `validation_brief.md`. Para cada job do lote:

1. Escolha o id do PP que melhor representa o job (`jobs.json[job].pocketphysio`).
   - Se o vídeo não estiver no cache, rode `pp_compare.py fetch <job>`.
   - Os ids com status `403` ou `placeholder` são julgados pelo texto.
2. Compare o nosso vídeo (`$V/videos/<job>.mp4`) com o do PP:
   - veja `/mnt/e/mannequin/avatar_man/out/compare/<job>.png`;
   - extraia quadros com ffmpeg e leia os PNGs **em tamanho real**;
   - meça as juntas com `uv run -q --no-project --with numpy python3 tool/mannequin/ops/pts.py <job> <pontos>`. Esse script lê `$KINETI_FINAL/qa`; para medir uma versão sua, use `KINETI_FINAL=$W/out`.
3. Critérios: posição inicial, amplitude, braços e mãos, contatos (pé plano, mão ou joelho que desliza, membro no ar), ritmo e movimento errado.
4. Dê o veredito `ok`, `ajustar` ou `refazer`, com notas curtas em português, como as do cliente.
5. Leia `contexto.json`. Um job que já é pendente conhecido só volta para correção se você tiver uma abordagem **diferente** das que falharam.

Saída: `$V/final/validation/lote_NN.json` (`{job: {ref, verdict, issues, resumo}}`).

### Corrigir

Siga `fix_brief.md`, com os caminhos trocados, para os jobs `ajustar` e `refazer`.

- **Só edite moves cujo dono é o seu lote** (`move_owner.json`). Se outro lote for dono do move de um job seu, registre o pedido em `report.json` → `_pedidos` (`{move: "o que mudar e por quê"}`).
- Para cada move: edite `$W/moves/*.json`, depois rode `mannequin.py build <move>` e `mannequin.py sync <move>`.
  - Mantenha o formato do arquivo: `json.dumps(doc, ensure_ascii=False, indent=1)`, sem quebra de linha no fim.
- Valide nesta ordem:
  1. **Números.** Folga ≤ 3 cm em repouso, penetração ≤ 1 cm, deslize ≤ 2 cm enquanto plantado. Meça as mãos perto do chão **depois** do `plant_hands`, como em `/mnt/e/mannequin/avatar_man/fix/lote_R2c/postplant.py`.
  2. **QA.** Nenhum `quebrado` novo na camada 1 e nenhum pop novo na camada 2, comparando com `qa_before`.
  3. **Stills.** `SHEET_FRACS=0,0.25,0.5 SHEET_NAME=fix python3 tool/mannequin/mannequin.py sheet <ids>`. Apague `$W/out/stills/<job>` antes.
- Faça no máximo ~4 tentativas por job. Se não funcionar, reverta o move e registre o `motivo`.
- Aplique a correção aos irmãos do lote e registre cada um em `_siblings`, inclusive os que ficaram de fora, com o motivo. Irmãos de outros lotes vão para `_pedidos`.
- Pedidos comuns:
  - "mais devagar": `beat` e/ou `hold` × 1,4–1,6, conferindo que o loop continua limpo;
  - "de frente": `jobs_change {"view": "front"}` ou `"front3q"`.
- Mudanças que exigem código (construtor, `plant_hands`, props, render) **não** entram no lote. Descreva a proposta exata em `_codigo`.

Saída: `$W/report.json`, no formato de `08-correcao.md`, com o `jobs_change` **plano** e as chaves `_siblings`, `_pedidos` e `_codigo`, mais os moves editados em `$W/moves/`.

O agente responde em até 250 palavras: contagem de ok, ajustar e refazer; quantos foram corrigidos e quantos não; moves alterados; pedidos para outros lotes; propostas de código.

### Coordenador, depois de cada lote

1. Confira o `report.json` por amostragem: veja os stills de 3 jobs corrigidos.
2. Junte as correções na worktree: `source $V/env.sh && python3 tool/mannequin/ops/merge_fix.py NN`. O script grava em `$WT/tool/mannequin` e em `$V/ops/rerender_ids.txt`.
3. Confira que nada mudou no repo principal: `git -C $MAIN status --short tool/mannequin` deve continuar vazio.
4. Passe os `_pedidos` para o agente do lote dono, se ele ainda não tiver começado. Se já terminou, junte os pedidos numa rodada extra `lote_X1`, que segue as mesmas regras.

Se o lote dono já tiver terminado, mude o move a partir da versão **atual** da worktree.

## Fase 3 · Montar a versão nova (coordenador)

Comece só depois de todos os lotes e rodadas extras terminarem.

1. **Sync da lib v10:**
   ```bash
   source /mnt/e/mannequin/avatar_man/v10/env.sh
   cp $V/lib.blend $V/lib_before_sync.blend
   cat $V/fix/lote_*/merged_moves.txt | tr ' ' '\n' | grep . | sort -u > $V/ops/moves_v10.txt
   export MANNEQUIN_AVATAR=$V/lib.blend MANNEQUIN_OUT=$V/final
   python3 tool/mannequin/mannequin.py build $(cat $V/ops/moves_v10.txt)
   python3 tool/mannequin/mannequin.py sync $(cat $V/ops/moves_v10.txt)
   ```
2. **Lotes de re-render:**
   - parta de `$V/ops/rerender_ids.txt`;
   - confira que os jobs que só mudaram por `jobs_change` estão incluídos;
   - grave `$V/final/lotes/lote_R01.txt`, `R02`… com ~50 ids cada.
3. **Render:** `tool/mannequin/ops/rerender_gate.sh 2`, com o `env.sh` da v10 carregado.
   - Os vídeos saem em `$V/videos/`, por cima das cópias da entrega atual, e o QA sai em `$V/final/qa`.
   - Acompanhe em `$V/ops/rerender_run.log`.
4. **Revisão visual** de cada lote R, com `layer4R_brief.md`. A saída vai para `$V/final/visual_review/lote_RNN.json`.
5. **Job que piorou:**
   - volte o vídeo com `cp /mnt/e/mannequin/avatar_man/out/videos_final/<job>.mp4 $V/videos/`;
   - reverta o move em `$WT` para a versão do `$MAIN`;
   - refaça build e sync desse move;
   - marque o job como `pendente`.

   Se o move for compartilhado, re-renderize os outros jobs que o usam.
6. **Consolidar:** `python3 tool/mannequin/ops/final_merge.py`. Ele grava em `$V/final/review.csv` e em `$V/final/pendentes_final.json`.
7. **Antes e depois:** para cada job com vídeo novo, monte `$V/antes_depois/<job>.mp4` com o vídeo da entrega atual à esquerda e o da v10 à direita, cada um em 960×540, com `hstack` no ffmpeg (use `-nostdin`). Faça também uma folha de contato por lote R.
8. **Lottie:** os Lotties dos jobs com move alterado ficaram desatualizados. Liste esses jobs em `$V/lottie_regen.txt`, no formato do `gen_jobs.sh` (`09-lottie.md`). **Não** gere os Lotties.
9. **Resumo:** escreva `$V/MUDANCAS.md` e `$V/mudancas.csv` (`job;move;veredito_antes;veredito_v10;o_que_mudou;status`). Inclua:
   - totais (ok, corrigido, pendente) antes e depois;
   - a lista de moves e `jobs_change`;
   - as propostas de código (`_codigo`), agrupadas e com o número de jobs que cada uma resolveria;
   - os pedidos que ficaram sem atender;
   - o diff da worktree: `git -C $WT diff --stat`.

**PARE** aqui. Aplicar a v10 na entrega (merge no `main`, lib final, `videos_final`, catálogo) é decisão do dono do projeto.

## Resposta final

Responda em português, com até 400 palavras:

- totais antes e depois (ok, corrigido, pendente) e quantos vídeos são novos na v10;
- os principais tipos de defeito encontrados e quantos jobs cada um afetou;
- os jobs não corrigidos e por quê, com até 20 linhas (o resto fica em `MUDANCAS.md`);
- as propostas de código, com o número de jobs que cada uma resolveria;
- os caminhos de `$V/MUDANCAS.md`, `$V/antes_depois/`, `$V/videos/`, `$V/lottie_regen.txt` e o branch da worktree (`revisao-v10`);
- qualquer desvio destas instruções, com o motivo.
