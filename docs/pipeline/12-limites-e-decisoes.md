# 12 · Limites, decisões e lições

## Decisões do dono do projeto

| Data | Decisão |
|---|---|
| 07/11 | Não usar mais Gemini nem Vertex (texto, imagem, vídeo). Perguntar antes de usar qualquer outro modelo externo pago |
| 07/11 | Padronizar o app no pipeline do manequim (depois, avatar e Lottie) |
| 12/11 | Avatar v9 (low-poly + cabelo) aprovado. Não mudar a aparência sem perguntar |
| 13/11 | Tranco 12°/quadro em caminhadas e avanços (8 nos demais); punho até 90° com carga; pausas do texto limitadas a 5 s; ritmo terapêutico acima da duração antiga; ids "diferente" saem do job |
| 13/11 | Ponte unipodal: **sem ponte**. Tronco no chão, joelho E dobrado, perna D esticada sobe a 50°. Não voltar para a ponte |
| 13/11 | Pausas de ~2 s no pico mantidas |
| 14/11 | Lottie aprovado. Pedidos: mãos melhores, sem piscar, props |
| 15/11 | Correção da mão em garra testada e **não aplicada**. Não aplicar sem perguntar de novo |
| 15/11 | Badge do catálogo continua mostrando o status da correção, e não o veredito final |

## Pendências abertas (33 no 3D)

Lista completa em `E:\mannequin\avatar_man\final\pendentes_final.json`.

**Precisam de código:**
- **Mão em garra no apoio** (bridge-ball-squeeze, prone-relaxed, high-sit-hand-slide-back, chair-arm-rotation-supported, e o tranco da mão em chair-diagonal-reach). Causa: o osso da mão do avatar tem ~30° de diferença em relação à palma (não aparece na malha em repouso). Teste em `E:\mannequin\avatar_man\fix\plant_test`:
  - `after/plant_hands.py` inclina a sola 30° para cima no `flatten`, com efeito reduzido em antebraços inclinados para trás;
  - multiplica o peso de repouso por 3;
  - roda as versões antiga e nova e só fica com a nova se penetração, folga, deslize e garra não piorarem.
  O resultado: 87 movimentos melhoram e 32 voltam ao comportamento antigo. Comparação em `final\teste_mao_antes_depois.png`. Aplicar exige re-renderizar os jobs afetados.
- **Âncora da pelve no construtor:** o `settle()` briga com `pos` e faz o corpo deslizar em bed-prop-on-elbows, pular em lying-to-sitting e dar tranco na pelve em standing-windmill-rotation. Mudança média, poucos vídeos.
- **Props:** halter numa mão só + mesa sob o cotovelo (rosca como no PP); faixa presa na sola (leg press); segundo halter (side-lying IR); faixa escondida (long-sit band inversion); bola dentro do joelho (wall iso knee extension); marcas que voltam no loop (step-to-marks).

**Corrigíveis numa próxima rodada de movimento:**
- mãos fora do lugar: chair-hamstring-stretch, seated-side-bend, figure-four-stretch, floor-butterfly-stretch (o contato fazia o antebraço atravessar a perna; 5–6 tentativas falharam), chair-neck-flexion-stretch, chair-pelvic-tilt-table, ball-plank-forearms, walker-mini-squat, bed-walker-sit-to-stand, jump-twist;
- trancos e emendas: floor-head-to-knee-easy, variable-speed-walking, chair-triceps-dips, chair-kneel-weight-shift, pulse-squat-jump;
- pose e amplitude: pistol-squat, low-lunge-kneeling, side-step-high-knee, iso-hip-extension-standing, chair-iso-ankle-dorsiflexion, supine-straight-leg-lower, wall-ball-squat-adductor-ball.

**Lottie:** regerar os ~595 restantes com os drivers melhorados (~3 h).

## Limites do rig e do render

- Sem dedos (só o grip por shape key), sem rosto, sem clavícula, coluna em um osso.
- Contato automático só com o chão e as caixas de `ground`. Mão no encosto ou na parede funciona porque o acessório é posto onde a mão está.
- Aterramento geométrico: o ponto mais baixo encosta. Uma pose pode apoiar na cabeça e nos pés com a pelve no ar.
- Os movimentos do desk-break foram feitos para a mão em bloco do manequim. O `plant_hands` precisa espalmar a mão do avatar.
- Mãos em apoios elevados (mesa, cadeira, beira da cama) ainda podem ficar na ponta dos dedos em alguns casos.
- Os 9 close-ups de mão não têm versão com avatar nem Lottie.

## Abordagens tentadas e revertidas

- **Construtor:**
  - fade de contato por deslocamento: sem efeito;
  - limite simétrico de queda da pelve: quebrou a caminhada;
  - limite de velocidade de dobra em todos os modos: criou emendas no loop;
  - deslocamento automático de equilíbrio no apoio unipodal: pernas alternadas pioraram.
- **Mão em garra:**
  - inclinação da sola medida na malha (1–2°): errada, a diferença real é ~30°;
  - 30° fixo sem redução: quebrou o alongamento de panturrilha (punho estendido demais, braço forçado na vertical).
- **QA:** a razão de jerk sozinha marcava quase todo movimento. Agora só ≥ 6°/quadro² absoluto conta como quebrado.
- **Suavização global:** proibida, porque solta os contatos.

## Lições operacionais

- **GPU:** no máximo 2 renders. Mais que isso é mais lento.
- **Pós-processamento** (comparação com o PP) é o gargalo de CPU: ~2,5 h por lote. Rode em paralelo com o render do lote seguinte.
- `merged_moves.txt` sem quebra de linha no fim: concatene com `cat f; echo`.
- `pgrep -f` acha o próprio shell. Use `pgrep -x blender.exe`.
- Faça backup da lib antes de toda sincronização grande. A lista está em `E:\mannequin\avatar_man\exercises_final_before_*.blend`.
- Os scripts e o estado das rodadas ficavam na pasta temporária da sessão e se perdiam. Agora ficam em `tool/mannequin/ops/` e `E:\mannequin\avatar_man\ops/`.
- Avatar e rig: o `lowpoly.py` do git difere do build aprovado. A versão de 10/11 só existe como `.pyc`, guardado em `E:\mannequin\avatar_man\lowpoly_aprovado_20261110.cpython-313.pyc` (a cópia do `__pycache__` do repo foi recompilada e se perdeu). O rig 2D antigo do kineti_app (`tool/lottie`) já foi apagado por um `git clean` uma vez. Versione o que importa.
