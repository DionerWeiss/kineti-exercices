# 04 · Câmera e acessórios

A lista completa de acessórios, com o que cada um faz, está em [tool/mannequin/README.md](../../tool/mannequin/README.md#câmera-e-cenário). Este documento trata da escolha.

## Campos do job

```json
"kineti-supine-hip-abduction": {"lib": "kineti", "view": "floor", "props": [], "pocketphysio": ["65b09dc54ad825d03040725f"]}
```

- `lib`:
  - `kineti` (movimento em `kineti_moves.json`);
  - `deskbreak` (em `deskbreak_moves.json`);
  - `hand` (close-up da mão, `scene` de `export_hand.py`; não tem versão com avatar).
- `view`: `side`, `front`, `side3q`, `front3q`, `rside3q`, `back3q`, `back`, `top3q`, `floor` e `close`. Distribuição atual: side3q 256, front3q 131, floor 100, side 78, front 59, top3q 26, rside3q 25.
- `frame`: `full` (padrão), `upper` (da cintura para cima) ou `lower` (dos joelhos para baixo).
- `props`: lista de acessórios.
- `move`: reaproveita o movimento de outro job com acessórios diferentes (por exemplo, a marcha sentada na bola usa `chair-march`).

## Escolha da vista

| Caso | Vista |
|---|---|
| Movimento no plano frontal (abdução, transferência de peso lateral, toque cruzado no joelho, inclinação lateral, passo lateral) | `front` (pedido do cliente). `front3q` se ler melhor |
| Agachamento, avanço, ponte, flexão, marcha | `side` ou `side3q` |
| Deitado | `floor` (lateral e alta). Com o corpo ao longo do eixo X, as vistas giram 90°, então "lado" continua de través |
| Prancha lateral | `side3q`. Na `side`, o corpo parece levitar, e na `floor` o antebraço some |
| Flexão na cadeira | `side` (o encosto escondia a cabeça na `side3q`) |
| Algo que acontece atrás do corpo | `back` |
| Pés sentado | `side3q` com `frame: lower` |
| Pescoço e ombros | `frame: upper` |
| Movimentos do desk-break (vêm girados `hips [0,-70,0]`) | `front`, senão a `side` mostra as costas. O render segue a rotação do peito quando a figura está em pé e girada mais de 25° |

Regras:
- `lower` nunca para quem está em pé (corta na coxa).
- **Paredes dos acessórios bloqueiam a câmera.** Com parede à frente, use `side`, e não `front3q`.
- O enquadramento projeta os vértices de todos os quadros (mais os acessórios, sem colchonete e parede) e ajusta largura e altura separadamente.
- Mudanças só de vista vão como `jobs_change: {"view": "front"}` e **não** aparecem na lista de "jobs com movimento alterado". Renderize-os à parte.

## Acessórios: cuidados

- **Colchonete:** só aparece sem `chair`, `ball`, `support` ou `wall`, e cobre a área do corpo em todo o movimento.
- **Cama (`bed`):** o colchão fica no nível do chão do rig, e o piso do quarto 50 cm abaixo.
- **Bola de apoio (`ballfeet/ballarms/ballhands/ballback`):** a parte apoiada precisa ficar a ~50–55 cm do chão. O log `BALL <id> <tipo> float <x> pen <y>` mostra a maior folga e a maior penetração; `BALL_DEBUG=1` lista os quadros com folga acima de 2 cm.
- **Andador (`walker`):** manoplas a 0,88 m (`WALKER_H`), presas nas mãos do primeiro quadro em que elas ficam 20 cm à frente da pelve.
- **Cadeira/encosto (`support`, `side`):** o render prende as mãos no encosto (`plant pin_sides`, IK de 2 ossos), para a elevação de panturrilha ou o agachamento apoiados não soltarem as mãos.
- **Mesa (`table`):** esconde a caixa de `ground` sob as mãos.
- **Rolo (`roll`):** ajustado às pernas (o maior rolo em que nenhum vértice da perna entra).
- **Faixa (`band-<a>-<b>`), bastão (`stick…`), toalha:** são refeitos a cada quadro entre as pontas. As mãos que seguram ganham grip.
- **Caminhada (`walk`):** a câmera segue a pelve e o piso é quadriculado (60 cm). O deslocamento do vídeo precisa ser múltiplo do quadrado, e também do degrau na escada de agilidade.
- **Props que ainda faltam** (pendências que precisam de código): halter numa mão só, mesa sob o cotovelo na rosca, faixa presa na sola no leg press, segundo halter no deitado de lado, bola na parede no joelho, marcas que não voltam no loop.
