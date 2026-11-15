# 08 · Rodadas de correção

## Ciclo por lote

Os 688 jobs foram divididos em 14 lotes de 50 (`final/lotes/lote_NN.txt`). Cada lote seguiu este ciclo:

```
render (ops/batch.sh NN)
  → validação contra o PP  (agentes/validation_brief.md → final/validation/lote_NN.json)
  → camada 3 por id do PP  (agentes/layer3_brief.md     → final/pp_review/lote_NN.json → ops/merge_pp.py NN)
  → camada 4 visual        (agentes/layer4_brief.md     → final/visual_review/lote_NN.json → ops/merge_visual.py NN)
  → correção               (agentes/fix_brief.md        → fix/lote_NN/report.json + moves → ops/merge_fix.py NN)
  → re-render dos jobs alterados em lotes R01…  (ops/rerender_gate.sh 2)
  → camada 4 do re-render  (agentes/layer4R_brief.md    → final/visual_review/lote_RNN.json)
  → pendências novas → rodadas extras (R2a, R2b, …) → mais lotes R
  → ops/final_merge.py → review.csv, pendentes_final.json
```

Nos lotes 01–02, cerca de 2/3 dos jobs precisaram de ajuste.

## Diretório isolado de correção

Cada rodada trabalha em `W=/mnt/e/mannequin/avatar_man/fix/lote_<nome>`, com cópias próprias dos movimentos e da lib. Assim a lib de render e o repo não mudam no meio de um render.

```bash
mkdir -p $W/out $W/moves
cp tool/mannequin/{kineti_moves,deskbreak_moves}.json $W/moves/
cp /mnt/e/mannequin/avatar_man/exercises_final.blend $W/lib.blend
export MANNEQUIN_MOVES_DIR=$W/moves MANNEQUIN_OUT=$W/out MANNEQUIN_AVATAR=$W/lib.blend MANNEQUIN_RES=1920x1080
```

Regras da rodada:
1. Rode o QA em todos os jobs da rodada **antes** de editar e guarde uma cópia. Uma correção está pronta quando atende à nota e não cria um `quebrado` novo na camada 1.
2. Valide com números (posições das juntas, `_low` de contato), depois com o QA e por fim com stills:
   - em repouso, folga ≤ 3 cm;
   - nenhuma penetração > 1 cm;
   - deslize ≤ 2 cm enquanto plantado.
   Ponha os números em `correcao`.
3. No máximo ~4 tentativas por job. Se não funcionar, reverta o movimento e explique.
4. Não repita uma abordagem que já falhou: procure em todos os `fix/lote_*/report.json`.
5. Mudanças de job (vista, props) vão em `jobs_change` **plano**: `{"view": "front"}`, e `null` apaga a chave.

Formato do `report.json`:

```json
{"<job>": {"move": "<id>", "status": "corrigido" | "não corrigido",
           "correcao": "<curto, em português>", "motivo": "<se não corrigiu>",
           "qa_before": "...", "qa_after": "...", "still": "<png>",
           "jobs_change": {"view": "front"}},
 "_siblings": {"<job>": "o que mudou / por que ficou de fora"}}
```

## Juntar no repositório

```bash
python3 tool/mannequin/ops/merge_fix.py <nome>
```

O script:
- traz os movimentos com status `corrigido` que mudaram;
- aplica `jobs_change`;
- grava `fix/lote_<nome>/merged_moves.txt`;
- acrescenta em `$KINETI_OPS/rerender_ids.txt` os jobs que usam movimentos alterados e os jobs com `jobs_change`.

Depois:
- faça backup da lib, depois `build` + `sync` dos movimentos juntados ([05](05-render.md#sincronizar-a-lib-final));
- monte os lotes de re-render `final/lotes/lote_RNN.txt` (~50 ids cada) a partir de `rerender_ids.txt`;
- `ops/rerender_gate.sh 2`.

Mais de uma rodada pode rodar ao mesmo tempo se cada uma tiver o seu grupo de jobs. Liste no brief os jobs que pertencem a outra rodada (veja [agentes/client_round_brief.md](agentes/client_round_brief.md)).

## Notas do cliente

1. O cliente revisa no catálogo e exporta um CSV (`id;nota`). O botão é "Exportar notas (CSV)" na página local; no app, as notas ficam em `catalog_reviews`.
2. Agrupe as notas por tema (cama/andador, ritmo/vista/equilíbrio, props…) e dê a cada grupo uma rodada `C1`, `C2`… com o brief [agentes/client_round_brief.md](agentes/client_round_brief.md).
3. As palavras do cliente valem mais que as notas de revisores anteriores. "Igual ao PocketPhysio" = assista o vídeo do PP e copie pose, amplitude, lado e ritmo.
4. Para cada nota, procure os irmãos (mesma família, mesmos props, mesmo tipo de movimento) e aplique quando fizer sentido. Registre em `_siblings` cada irmão alterado ou deixado de fora, com o motivo.
5. Pedidos comuns:
   - "mais devagar": `beat` e/ou `hold` × 1,4–1,6, mantendo contatos e loop;
   - "de frente": `jobs_change {"view": "front"}` (ou `front3q`);
   - aparência do avatar: corrija pela pose. Se não der, explique no `motivo`. Não mude o modelo.
6. Responda ao cliente com: corrigido / não corrigido por nota, irmãos alterados e o que precisa de mudança fora dos movimentos (render, props), com a proposta exata.

Lote 01 (15/11): 32 notas, 29 corrigidas, 2 para confirmar, 3 não corrigidas (limite do construtor). As notas dos lotes 02–14 entram no mesmo fluxo.

## Lições das rodadas

- Correções feitas só com `jobs_change` (vista) não entram em "jobs com movimento alterado". Renderize-as à parte.
- O badge do catálogo mostra o status do último `report.json` da correção, não o veredito final. Alguns jobs aparecem como "não corrigido" e estão ok ou corrigidos ([10](10-catalogo-e-app.md)).
- Os bugs de movimento vistos ao gerar os Lotties vão para `puppet2d/final/move_bugs.txt` e `$KINETI_OPS/extra_fixes.txt`, e entram na rodada seguinte.
- Antes de cada rodada, guarde cópias dos arquivos que serão alterados (`jobs_before_<rodada>.json`, `kineti_moves_before_<rodada>.json`).
