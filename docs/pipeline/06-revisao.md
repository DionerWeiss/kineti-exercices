# 06 · Revisão em 4 camadas

Cada vídeo passa por quatro camadas. As duas primeiras são automáticas e saem do render com `QA=1`. As outras duas são feitas por pessoas ou agentes que olham as imagens.

| Camada | O que verifica | Ferramenta | Saída |
|---|---|---|---|
| 1 · Pose | contatos, deslize, palma, malha, roupa, acessórios, câmera | `qa_pose.py` | `final/qa/<job>.json` |
| 2 · Movimento e vídeo | trancos, jerk, loop, amplitude (ROM), equilíbrio, legibilidade, ritmo, quadros congelados | `motion_qa.py` → `motion_review.py`; `video_qa.py` | `qa/<job>.motion.npz/.json`, `qa/<job>.video.json` |
| 3 · PocketPhysio | o exercício é o mesmo do PP? | `pp_compare.py` + agente ([07](07-pocketphysio.md)) | `final/pp_review/lote_NN.json` → `review_pp.json` |
| 4 · Visual | o defeito aparece? a correção aparece? | agente ou pessoa | `final/visual_review/lote_NN.json` → `review_notes.json` |

`review.py` junta tudo em `review.csv` (uma linha por job) e `review_pp.csv` (uma linha por job e id do PP). A coluna `final` é o veredito visual quando existe. Sem ele, fica `ok` se todas as camadas automáticas estiverem ok, ou `pendente` ("aguarda revisão visual") se alguma marcou problema.

```bash
cd tool/mannequin && python3 review.py /mnt/e/mannequin/avatar_man/final /mnt/e/mannequin/avatar_man/out/videos_final [ids.txt] [nome.csv]
```

Severidade: 1 = suspeito, 2 = quebrado. O status de cada camada é o pior problema encontrado.

## Camada 1 · Pose (`qa_pose.py`)

Mede a cena pronta (depois do `plant_hands`, com acessórios e câmera) sem mudar nada. Limites em `TH`:

| Checagem | Limite |
|---|---|
| Mão ou pé parado acima do apoio | 2–6 cm por ≥ 10 quadros (parado = < 4 mm/quadro) |
| Corpo dentro do chão ou de um acessório | 2 cm suspeito, 4 cm quebrado (um ponto ao lado da borda de uma caixa conta como fora) |
| Deslize de contato plantado | 3 cm suspeito, 8 cm quebrado |
| Palma de apoio | cos(ângulo com o apoio) ≥ 0,6. Sentado, só conta a mão no chão (no assento a mão segura a borda) |
| Membro dentro do corpo (além da pose de repouso) | 1,5 cm suspeito, 3,5 cm quebrado |
| Pele saindo pela roupa / barra afastada | 6 mm / 3 cm. Gola > 4 cm e coxa > 3 cm = quebrado |
| Bola descolada ou dentro do corpo; mão longe do que segura | 2,5 / 4 / 3,5 cm |
| Cabelo dentro da cabeça / do chão | 8 mm / 1 cm |
| Câmera | > 0,2% dos vértices fora do quadro, ou figura de costas |

## Camada 2 · Movimento (`motion_review.py`) e vídeo (`video_qa.py`)

```bash
cd tool/mannequin && uv run -q --no-project --with numpy python3 motion_review.py /mnt/e/mannequin/avatar_man/final/qa <ids>
```

| Grupo | Checagem e limite |
|---|---|
| Fluidez | tranco > 8°/quadro (12 em caminhadas e avanços); jerk ≥ 6°/quadro² é quebrado (abaixo de 1° não se vê); pelve teleporta > 3 cm/quadro com os dois pés no chão; desaceleração no fim de cada trecho; loop (último quadro × primeiro: 2°, 1 cm) |
| Biomecânica | limites anatômicos (`LIMITS`, tolerância 5°): joelho −5…160, cotovelo −5…150, quadril flexão −20…125, abdução −30…45, rotação ±60, coluna flexão −30…80, inclinação ±35, rotação ±45, pescoço, tornozelo −50…20, punho até 85 (90 com carga); equilíbrio (centro de massa a 3 cm / 8 cm fora da base); simetria; ritmo (2–5 s por repetição); pausas |
| Legibilidade | parte que se move visível (≥ 15%), plano de frente para a câmera, amplitude na tela, câmera rasante sobre o corpo no chão (< 14°) |
| Vídeo | número de quadros, 1920×1080 a 30 fps, quadros congelados, cintilação, início parado ≥ 0,5 s |

Movimentos balísticos (saltos, corrida) não checam tranco nem teleporte. Movimentos de passo não checam equilíbrio com um pé no ar.

## O que o automático **não** pega

- **Mão, antebraço ou joelho flutuando** acima do apoio (a camada 1 mede o efetor parado, mas antebraços e joelhos escapam). Julgue pela sombra e pela superfície, em recorte de tamanho real, e meça o `_low` (≤ 3 cm de folga).
- Movimento diferente do PP (amplitude, braços, posição inicial): isso é da camada 3.
- Muitas marcações pequenas (pele 1–2 cm pela roupa, autocontato de 2–4 cm) não aparecem no vídeo. Se não dá para ver, o veredito visual é `ok`.

## Camada 4 · Revisão visual

Instruções completas: [agentes/layer4_brief.md](agentes/layer4_brief.md) (primeira passada) e [agentes/layer4R_brief.md](agentes/layer4R_brief.md) (re-render).

1. **Mosaico de 8 quadros** de cada vídeo:
   ```bash
   N=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 V.mp4)
   ffmpeg -v error -y -i V.mp4 -vf "select='not(mod(n\,$((N/8))))',scale=480:-2,tile=4x2" -frames:v 1 tile.png
   ```
2. Quando a checagem ou a correção fala de um contato ou de um quadro, extraia esse quadro em tamanho real e recorte a parte do corpo.
3. Primeira passada: olhe todo job com alguma camada diferente de `ok`, mais 1 em cada 10 (posições 1, 11, 21…). No re-render, olhe **todos**.
4. Defeitos que importam:
   - membro atravessando o corpo, um acessório, a parede ou o chão;
   - mão, antebraço, joelho ou pé claramente no ar;
   - pé patinando;
   - tranco entre quadros;
   - corpo cortado (close-ups são de propósito);
   - câmera de costas quando o exercício pede frente;
   - acessório fora da mão;
   - pose anatomicamente errada;
   - movimento que não é o exercício.
5. O visual low-poly e o sombreado simples são de propósito. Não aponte detalhes de estilo.

Veredito:

```json
{"<job>": {"visual": "ok" | "corrigido" | "pendente", "nota": "...", "correcao": "...", "motivo": "..."}}
```

- `corrigido` = o relatório de correção diz corrigido **e** o vídeo novo mostra a correção (copie o texto de `correcao`).
- `pendente` = o defeito continua ou apareceu outro. O `motivo` diz o quê e em que quadro.
- Pendências conhecidas que ainda aparecem continuam `pendente`.

Junte com `ops/merge_visual.py NN`. No fim, `ops/final_merge.py` junta todas as revisões visuais na ordem lotes 01–14 e depois R01…Rnn (a mais recente ganha) e refaz `review.csv` e `pendentes_final.json`.

## Folha de contato

```bash
cd tool/mannequin && python3 contact_sheet.py <videos> <ids.txt> <out.png> [<qa dir> [cols]]
```

Uma linha por vídeo, com 6 quadros, o id e o status automático.

## Armadilhas aprendidas

- A imagem engana (mãos pareciam apoiadas e estavam 5 cm acima). Confie na medida, depois olhe.
- Some o deslize como vetor, com zona morta. Use a orientação da palma, não a fração de vértices, para pegar mão na ponta dos dedos.
- A mão de lado na prancha lateral está certa.
- O sinal da distância a uma caixa só conta "dentro" quando o deslocamento vai contra a normal da face. Ao lado da borda, não conta.
- Mãos que nunca chegam a 12 cm de um objeto não estão segurando nada.
- Bola entre os joelhos não é cadeira. O render passa o próprio `seated` para o QA.
