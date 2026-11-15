# 03 · Criação de movimentos

Os movimentos ficam em `tool/mannequin/kineti_moves.json` (ids `kineti-*`) e `deskbreak_moves.json` (ids do desk-break). O formato é o do desk-break (`build/desk-break/library/AUTHORING.md`), com as extensões `ground` e `touch`. Ao gravar, mantenha `json.dumps(doc, ensure_ascii=False, indent=1)` **sem quebra de linha no fim**.

## Formato

```json
{"id": "kineti-mini-squat", "en": "Mini squat, arms forward", "amount_en": "10",
 "steps_en": ["Arms forward at shoulder height.", "Bend the knees a little, hips back.", "Stand back up."],
 "beat": 1.2,
 "keys": [
  {"arm": [0, 0, 6], "leg": [0, 0, 4]},
  {"arm": [-118, 0, 6], "leg": [-75, 0, 4], "knee": [92, 0, 0], "foot": [-24, 0, 0],
   "spine": [28, 0, 0], "neck": [-14, 0, 0], "pos": [0, 0, -0.24], "hold": 0.4}
 ]}
```

| Campo | Significado |
|---|---|
| `beat` | Segundos por transição entre poses |
| `keys` | Poses: `{osso: [x, y, z] em graus}`. Osso sem sufixo vale para os dois lados (`arm`, `leg`, `knee`, `foot`, `elbow`, `hand`) e `armL`/`armR` vale para um lado só. Há também `hips`, `spine` e `neck` |
| `hold` | Segundos parado naquela pose |
| `pos` | Deslocamento da pelve `[x, y, z]` em metros: x = esquerda da figura, z > 0 para a frente, z < 0 para trás |
| `touch` | Contatos a resolver: `["footL"]` dobra o joelho até o pé tocar, `["footL:leg"]` gira o quadril, `["hand:arm"]` resolve a mão esquerda pelo ombro e copia o ângulo para a direita |
| `lift` | Metros acima do chão (saltos) |
| `once` | Não repete em loop. Caminhadas terminam na pose inicial, deslocadas um número inteiro de quadrados do piso |
| `ground` | Campo de alturas `{"base": 0, "boxes": [[xmin, xmax, ymin, ymax, h], …]}` em metros, no mundo do Blender (a figura olha para −y) |

As poses repetem em loop (da última volta para a primeira), a menos que o movimento tenha `once`.

## Convenções de sinal

| Osso | Convenção |
|---|---|
| `leg` | x < 0 flexão do quadril, x > 0 extensão; z > 0 abdução; y = rotação da coxa (45 = pés para fora) |
| `knee` | x > 0 dobra |
| `foot` | x < 0 dedos para cima, x > 0 dedos para baixo (ponta dos pés ~35–50); `foot [0,-25,0]` vira os dedos para dentro (inversão); z não faz nada visível |
| `arm` | x < 0 levanta o braço para a frente (−90 = horizontal à frente em pé). É relativo ao tronco, então inclinar o tronco muda o resultado. z > 0 levanta para o lado (90 = T, 180 acima da cabeça, ~200 mãos juntas acima da cabeça) |
| `elbow` | x < 0 dobra |
| `hand` | x > 0 flexiona |
| `spine` | x > 0 flexão; z = inclinação lateral; y = rotação |
| `hips` | `[-90,0,0]` deitado de costas; `[0,-70,0]` girado (é assim que os movimentos do desk-break vêm, então a vista `side` mostra as costas); `[-59,90,0]` prancha lateral sobre o lado esquerdo (x menos negativo levanta a cabeça); `[67,0,0]` prancha de frente com os braços perpendiculares ao tronco |

## Como o construtor se comporta

- **Aterramento:** em cada pose, o ponto mais baixo encosta na superfície. Uma pose pode "apoiar" na cabeça e nos pés com a pelve no ar. As linhas `KEY` do build (altura de pés, mãos e pelve por pose, em movimentos com `ground`) servem para pegar isso. Exemplo: braços `[40]` deitado faz o corpo apoiar nas mãos.
- **Contatos presos:** um pé que pousa fica preso (IK). Ele só solta quando a própria perna o levanta mais de 6 cm (LIFT_HI), medido em relação à pelve. Se as poses o arrastam mais de 15 cm, ou se o joelho ou a canela apoiam, ele é preso de novo na pose dobrada, e daí nunca mais solta: fica grudado, com as pernas abertas. Portanto:
  - mantenha `pos` e os ângulos de perna coerentes, para o pé apoiado ficar parado;
  - pouse o pé que dá o passo com a perna longa (calcanhar primeiro);
  - levante-o de volta com o joelho alto;
  - não apoie o joelho de trás no chão sem querer.
- **Interpolação entre poses** pode levantar um contato em até 14 cm (por exemplo, os calcanhares entre a ponte e a flexão de joelhos na bola). Quando o contato importa, **acrescente uma pose intermediária**.
- **Agachar:** uma pose que baixa a pelve precisa de `pos [0,0,-drop]` (pelve para trás). Sem isso, o primeiro quadro inclina como uma prancha.
- **Caixa de `ground` sob a pelve** levanta o corpo inteiro para cima dela. Panturrilhas na cadeira: deixe a caixa só sob os pés (y ≤ −0,36).
- **Travesseiro sob a cabeça:** flexione um pouco o pescoço (`neck [14]` para 6 cm), senão a cabeça levanta o corpo inteiro.
- **Ponte:** os ombros ficam no chão (`armR` z ≈ 0,11). Meça com `ops/pts.py` antes de entregar.
- O `settle()` do construtor briga com `pos` em movimentos em que o corpo todo se desloca deitado ou sentado (`bed-prop-on-elbows` desliza, `lying-to-sitting` pula, a pelve do `windmill` dá tranco). Isso precisaria de uma opção de âncora da pelve no construtor ([12](12-limites-e-decisoes.md)).

## Truques que funcionaram

| Situação | Receita |
|---|---|
| Pé sai do chão sem raspar | Pose com flexão de quadril p e joelho ~2p (por exemplo leg −25, knee 55) antes de mover o pé, e a mesma pose na volta. Para tirar do chão, o pé também sobe: leg −18, knee 38, foot −20 |
| Contato fixo enquanto o corpo gira (joelhos na flexão de joelhos, pontas dos pés na flexão inclinada) | `pos` na pose para a pelve andar no arco em volta do contato (+0,06 a +0,08 para a frente), com a inclinação da pelve apontando as pernas para o pé apoiado |
| Avanço fundo (joelho no chão) | Perna da frente `[-92,0,0]`, joelho 106, pé −8; perna de trás `[10,0,0]`, joelho 98, pé 50 |
| Braços à frente com cotovelos dobrados | arm `[-95,0,10]`, elbow `[-95,0,0]` |
| Braços horizontais num agachamento com tronco a ~30° | arm `[-118,0,6]` |
| Pés planos deitado com joelhos dobrados | foot ~`[25,0,0]` com leg −45 e knee 95 (confira dedo z ≈ tornozelo z) |
| Mãos na barra do andador ao agachar | Caixa de `ground` na altura das manoplas + `touch: ["hand:arm"]` (o andador esconde a caixa) |
| Mãos ou antebraços sobre a bola | Caixa de `ground` invisível na altura do topo da bola e braços aduzidos (a bola é redonda) |
| Isometria | repouso → posição → posição com um empurrão mínimo, `hold 2.0` |
| Braços cruzados | `arm [-40,-65,15]`, `elbow -115` |
| Elevação de perna estendida deitado | Tronco no chão, joelho E dobrado, perna D esticada sobe a ~50° e desce (é o que o cliente quis no lugar da ponte unipodal) |

## Ritmo e pausas (o que o cliente pediu)

- **Ritmo terapêutico ganha** da duração do vídeo antigo. Um vídeo mais curto que a referência é só uma nota.
- Movimentos lentos de mesa (bombeamento de tornozelo, balanço calcanhar-ponta, marcha, elevação de joelho) estavam rápidos demais. Para "mais devagar", aumente `beat` e/ou os `hold` em 1,4–1,6×, mantenha os contatos e confira se o loop continua sem emenda.
- **Pausas** tiradas do texto do PP, limitadas a 5 s. Pausas de ~2 s no pico foram mantidas por escolha do cliente.
- Limite de tranco: 8°/quadro (12°/quadro em caminhadas e avanços).
- Extensão de punho até 90° é aceitável enquanto a palma sustenta peso.

## Testar um movimento sem tocar na lib final

```bash
W=/mnt/e/mannequin/avatar_man/fix/teste_x; mkdir -p $W/out $W/moves
cp tool/mannequin/{kineti_moves,deskbreak_moves}.json $W/moves/
cp /mnt/e/mannequin/avatar_man/exercises_final.blend $W/lib.blend
export MANNEQUIN_MOVES_DIR=$W/moves MANNEQUIN_OUT=$W/out MANNEQUIN_AVATAR=$W/lib.blend MANNEQUIN_RES=1920x1080
# edite $W/moves/kineti_moves.json
python3 tool/mannequin/mannequin.py build kineti-x && python3 tool/mannequin/mannequin.py sync kineti-x
python3 tool/mannequin/mannequin.py qa <job> 2>&1 | grep "^  QA "
(cd tool/mannequin && uv run -q --no-project --with numpy python3 motion_review.py $W/out/qa <job>)
rm -rf $W/out/stills/<job>; SHEET_FRACS=0,0.25,0.5 SHEET_NAME=fix python3 tool/mannequin/mannequin.py sheet <job>   # -> $W/out/fix_01.png
```

Posições das juntas: `$W/out/qa/<job>.motion.npz` traz `track` (nomes: `hips spine neck armL elbowL handL armR elbowR handR legL kneeL footL legR kneeR footR toeL toeR fingL fingR headtop`) e `pts` [quadro, ponto, xyz] em metros (z para cima, a figura olha para −y, +x é a esquerda dela). O `ops/pts.py` imprime essas posições (ele lê de `final/qa`; para outro diretório, ajuste o caminho).

Depuração do construtor: `KB_DEBUG=<id>` (eventos PLANT/RELEASE/SLID) e `KB_KEYS=1` (posição de mãos, pés e articulações em cada pose).

Atenção: `export_joints` a partir da lib **não** inclui o `plant_hands` do render. Para medir mãos depois do plant, rode o QA (camada 1), que mede a cena pronta.
