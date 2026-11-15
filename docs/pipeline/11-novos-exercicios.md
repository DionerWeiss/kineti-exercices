# 11 · Novos exercícios

Roteiro do zero até o catálogo para um exercício novo. Ainda há ~140–200 exercícios do PP viáveis e não cobertos: TUG, caminhadas com giro, movimentos com assistente e algumas isometrias (canto, bola na parede no joelho, multífido na beira da cama). Também há os 34 ids de `pp_removed.json`, que precisam de vídeo próprio.

## 1. Decidir se o rig consegue

Fica de fora (limite do rig): dedos, rosto, giro de cabeça (cabeça sem rosto não mostra rotação), respiração, tarefas de vida diária, massagem com os dedos, exercícios em dupla. Clavícula só via `arm.pos`, e a coluna é um osso só.

Antes de criar, procure um movimento existente:
- O exercício é o mesmo de outro job com outro acessório? Crie só o job, com `move` apontando para o movimento existente.
- O vídeo existente já serve? Acrescente o id do PP em `jobs.json[job].pocketphysio`, depois de julgar `igual` pela rubrica de [07](07-pocketphysio.md).
- Ids novos podem colidir com movimentos existentes. Confira `kineti_moves.json` antes.

## 2. Estudar a referência

```bash
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py fetch <job>   # depois de criar o job (passo 4); ou baixe o id direto
tool/mannequin/ops/pp.sh <ppid>                                                        # texto + mosaico de 8 quadros
```

Anote:
- posição inicial;
- amplitude máxima;
- braços;
- contatos que ficam parados;
- ritmo (segundos por repetição);
- pausas (do texto, limitadas a 5 s);
- de que lado a ação se vê melhor.

## 3. Escrever o movimento

Em `tool/mannequin/kineti_moves.json`, com o id `kineti-<nome>` ([03](03-movimentos.md)):
- comece de um movimento parecido e copie a estrutura;
- primeira pose = posição inicial do PP; poses intermediárias onde um contato precisa ficar parado;
- `beat` calmo (o cliente prefere devagar);
- textos em inglês (`en`, `steps_en`, `amount_en`) para manter o formato do desk-break.

## 4. Criar o job

Em `tool/mannequin/jobs.json`:

```json
"kineti-<nome>": {"lib": "kineti", "view": "side3q", "props": ["chair"], "pocketphysio": ["<id de 24 caracteres>"]}
```

Vista e acessórios: [04](04-camera-e-props.md). Movimento frontal → `front`.

## 5. Testar num diretório isolado

Siga [03 · Testar um movimento](03-movimentos.md#testar-um-movimento-sem-tocar-na-lib-final):
1. `build` + `sync` na lib de teste;
2. `qa` (camada 1) e `motion_review` (camada 2), sem `quebrado`;
3. medir contatos (folga ≤ 3 cm, penetração ≤ 1 cm, deslize ≤ 2 cm);
4. stills e comparação com os quadros do PP.

Linhas do build:
- `TOUCH`: ângulo resolvido;
- `KEY`: alturas por pose;
- `BALL`: folga e penetração da bola.

## 6. Levar para a lib final e renderizar

```bash
cp /mnt/e/mannequin/avatar_man/exercises_final.blend /mnt/e/mannequin/avatar_man/exercises_final_before_<nome>.blend
# ambiente de entrega (02-ambiente.md)
python3 tool/mannequin/mannequin.py build kineti-<nome> && python3 tool/mannequin/mannequin.py sync kineti-<nome>
QA=1 python3 tool/mannequin/mannequin.py render kineti-<nome>
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py compare kineti-<nome>
```

Para vários exercícios, ponha os ids num `final/lotes/lote_NN.txt` e use `ops/batch.sh NN`.

## 7. Revisar

- Camadas 3 e 4 ([06](06-revisao.md), [07](07-pocketphysio.md)): igual ao PP? algum defeito visível?
- Registre o veredito em `final/review_notes.json` e `final/review_pp.json` e rode `review.py`.

## 8. Lottie

Exporte as juntas da action, rode `pick_view.py` e gere com `gen_jobs.sh` ([09](09-lottie.md)). Confira: piscadas = 0, flutuação ≤ 5 px, props desenhados. Acrescente o job ao `manifest.json`.

## 9. Textos e catálogo

1. Nome, descrição, foco e área em `tool/mannequin/texts_pt.json` (à mão, descrevendo o que o vídeo mostra).
2. `python3 tool/mannequin/catalog.py`.
3. `python3 tool/mannequin/compare_catalog.py`.
4. App: copie `data.js`, `node scripts/sync-catalog.mjs`, `upload-catalog.mjs` e `npm run seed` (o seed é idempotente).

## Acessório novo

Quando o exercício precisa de um acessório que não existe:
1. **3D:** em `render_mannequin.py`, crie o objeto, posicionado a cada quadro a partir das juntas (veja `band-…` e `ballfeet` como modelo). Se algo apoia nele, use uma caixa de `ground` no movimento. Se a mão segura, ponha o material em `HELD_MATS` do `qa_pose.py`.
2. **QA:** contatos e penetração com o acessório (`qa_pose.py`: `NOT_ENV`, `BALL_MATS`, `OK_HITS`).
3. **2D:** desenhe o equivalente em `drive_puppet.py` (e no `drive_front.py`) no estilo plano, com cinzas e azuis suaves.
4. Documente no [README do manequim](../../tool/mannequin/README.md).

## Checklist de entrega

- [ ] Primeira pose = posição inicial do PP; amplitude e braços iguais ao vídeo
- [ ] Ritmo calmo; pausas do texto (≤ 5 s); loop sem emenda
- [ ] Contatos: folga ≤ 3 cm, sem penetração > 1 cm, deslize ≤ 2 cm (medido, depois visto)
- [ ] Camadas 1 e 2 sem `quebrado`
- [ ] Vista em que a ação aparece (frontal → `front`)
- [ ] Irmãos conferidos
- [ ] Lottie gerado e conferido
- [ ] Textos, catálogo e app atualizados
