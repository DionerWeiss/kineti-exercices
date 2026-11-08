# Vídeos com o manequim (desk-break + Kineti)

O manequim de madeira do [desk-break](https://github.com/shlomorsh/desk-break) (MIT, 435 exercícios), repintado com a paleta Kineti e com a marca no peito, mais os acessórios dos exercícios.

```bash
python3 tool/mannequin/mannequin.py setup            # clona o desk-break no commit fixado, em build/desk-break
python3 tool/mannequin/mannequin.py build            # kineti_moves.json -> build/mannequin/kineti_lib/exercises.blend
python3 tool/mannequin/mannequin.py sheet [ids...]   # 3 quadros por exercício -> build/mannequin/sheet_NN.png
python3 tool/mannequin/mannequin.py render [ids...]  # MP4 -> build/mannequin/videos/<id>.mp4
python3 tool/mannequin/catalog.py                    # catálogo em português -> tool/mannequin/catalog.json
```

## Arquivos

- **`jobs.json`:** um job por vídeo, com estes campos:
  - `lib`: `deskbreak` (movimento pronto da biblioteca) ou `kineti` (escrito em `kineti_moves.json`);
  - `view`: a câmera;
  - `props`: os acessórios;
  - `pocketphysio`: os ids do catálogo em `research/pocketphysio/` que o vídeo atende.
- **`catalog.json`** (gerado por `catalog.py`): um item por vídeo, no formato do `catalog.json` da biblioteca, com estes campos a mais:
  - `video`: o MP4 em `build/mannequin/videos/`;
  - `kineti_slug`: o exercício equivalente da biblioteca Kineti, quando há. Nos vídeos do desk-break, ele vem da comparação feita no PocketPhysio e é só indicativo;
  - `pocketphysio`: os ids atendidos.
- **`library_map.json`:** para cada um dos 59 exercícios da biblioteca Kineti, o vídeo do manequim que o substitui, ou `null` e o motivo. No catálogo, ele aparece no campo `substitui`.
- **`texts_pt.json`:** nome, descrição, foco e área de cada vídeo, escritos à mão (`{slug: [nome, descrição, foco, área]}`). A descrição segue o que o vídeo mostra, e não o texto original do desk-break. Os movimentos Kineti que já estão na biblioteca usam os textos do `catalog.json` dela.
- **`kineti_moves.json`:** movimentos escritos por nós, no formato do desk-break (veja `build/desk-break/library/AUTHORING.md`). Os ids começam com `kineti-`.
- **Close-ups da mão** (`lib: "hand"`): a mão de madeira com dedos, no estilo do manequim, apoiada na mesa. `export_hand.py` exporta, quadro a quadro, a cinemática da mão do Lottie (`tool/build_library_hand_animations.py`), com as mesmas verificações. Depois `render_hand.py` monta segmentos, articulações, palma, mesa e câmera no Blender. As cenas de `export_hand.py` são punho, antebraço, abrir e fechar a mão, oposição do polegar, apertar bola, dedos em L, flexão e abdução do polegar e desvio do punho.
- **`render_mannequin.py`:** roda dentro do Blender. Repinta o manequim, aplica a marca, monta o cenário e a câmera, e renderiza.
- **`kineti_builder.py`:** cópia do `library/build_library.py` do desk-break (commit 8d475aa, MIT) com duas adições. Sem elas, gera exatamente as mesmas curvas que o original:
  - `"ground"` no exercício: um campo de alturas `{"base": 0, "boxes": [[xmin, xmax, ymin, ymax, h], ...]}`, em metros no mundo do Blender (a figura olha para −y). O aterramento, as partes apoiadas, os pés e mãos presos e o empurrão para fora do chão passam a medir a altura acima da superfície sob cada vértice. Assim um pé apoia no degrau, ou o calcanhar fica para fora da borda. A ação guarda o campo em `act['ground']`. O `render_mannequin.py` desenha cada caixa como um degrau ou, quando o job tem `bed`, como uma cama com o topo na caixa (chão em `base`, como no deitado para sentado). Um pé preso é solto quando a pose o leva sobre uma superfície mais alta;
  - `"touch"` numa pose: ajuda de autoria. `["footL"]` dobra o joelho, e `["footL:leg"]` gira o quadril, até o pé tocar a superfície na mesma altura dos outros apoios (vale também para `handL`, com cotovelo ou `:arm`). Sem o lado (`hand:arm`), resolve o esquerdo e dá o mesmo ângulo ao direito. Escolhe a raiz mais perto do ângulo escrito e descarta as falsas da borda do degrau. O build imprime `TOUCH` com o ângulo resolvido e, em exercícios com `ground`, uma linha `KEY` por pose com a altura de pés, mãos e pelve.
- **`build_lib.py`:** roda o `kineti_builder.py` num arquivo de movimentos e salva o `.blend`, que o original só grava para a biblioteca inteira.

## Câmera e cenário

- **Enquadramento:** a câmera projeta os vértices do manequim, de todos os quadros amostrados, mais os acessórios (sem o colchonete e a parede), e ajusta largura e altura separadamente.
- **Vistas** (`DIRS` em `render_mannequin.py`): `side`, `front`, `side3q`, `front3q`, `rside3q`, `back3q`, `back`, `top3q` e `floor`. A `floor` é de lado e alta, para quem está deitado. A `back` olha as costas, para o que acontece atrás do corpo. Com o corpo deitado ao longo do eixo X, as vistas giram 90°, então "lado" continua sendo de través.
- **Colchonete:** cobre a área ocupada pelo corpo durante todo o movimento. Só aparece sem `chair`, `ball`, `support` ou `wall`.
- **Folga entre poses-chave:** a interpolação entre duas poses pode levantar um pé ou um antebraço vários centímetros. Por exemplo, os calcanhares sobem 14 cm entre a ponte e a flexão de joelhos na bola. Quando o contato com um acessório importa, acrescente uma pose intermediária.
- **Acessórios:**
  - `chair`: cadeira, com o manequim sentado;
  - `stool`: banqueta (cadeira sem encosto), com o manequim sentado. Serve quando algo passa atrás das costas;
  - `support`: encosto de cadeira à frente, na altura das mãos;
  - `side`: cadeira ao lado, com a mão que está mais afastada do corpo no encosto;
  - `wall`: parede logo à frente das mãos, virada para a direção em que as mãos vão a partir da pelve (funciona também com os movimentos do desk-break, que vêm girados);
  - `roll`: rolo sob o joelho;
  - `ball`: bola entre os joelhos, que achata. Só põe a cadeira quando a pelve está na altura do assento (agachamento em pé e ponte também usam a bola);
  - `cuff`: tornozeleira;
  - `dumbbell`: halteres nas mãos;
  - `bed`: cama. O colchão fica no nível do chão do manequim, então o contato automático continua funcionando, e o piso do quarto fica 50 cm abaixo. Substitui o colchonete;
  - `bandhands`: faixa elástica entre as mãos;
  - `bandanchor`: faixa das duas mãos até um batente à frente;
  - `bandanchor1`: o mesmo, só com a mão que mais se move;
  - `bandfeet`: faixa das mãos até os pés (em pé sobre a faixa, ou sentado com a faixa nos pés);
  - `bandknees`: alça em volta das duas coxas, logo acima dos joelhos;
  - `walk`: caminhada. A câmera acompanha a pelve e o piso fica quadriculado, para o avanço aparecer. O movimento usa `"once": true` e termina na mesma pose em que começa, deslocado um número inteiro de quadrados, então o vídeo emenda sem salto;
  - `chairfit`: cadeira sob a pelve da primeira pose, para sentar e levantar. Esse exercício não usa `seated`, que prenderia a pelve no assento;
  - `wallball`: parede atrás das costas e bola suíça entre a lombar e a parede;
  - `wallback`: parede encostada nas costas durante todo o movimento;
  - `swissseat`: bola suíça como assento, para exercícios sentados. Costuma vir com `move` reaproveitando o movimento da cadeira;
  - `table`: mesa sob a mão ou as mãos que ficam paradas. Com uma mão só, é uma mesa pequena de canto, como no pêndulo de Codman.
  - `step`: só o rótulo "Degrau" no catálogo. O degrau em si vem do `ground` do movimento.
  - `bandankles`: alça em volta dos dois tornozelos;
  - `band-<ponta>-<ponta>`: faixa entre duas pontas, refeita a cada quadro. Cada ponta pode ser:
    - uma parte do corpo: `hL`/`hR` (palma), `fL`/`fR` (sola, faixa passada pelo pé), `aL`/`aR` (tornozelo), `kL`/`kR` (joelho) ou `sL`/`sR` (atrás do ombro, faixa pelas costas);
    - um poste fixo: `F`, `B`, `L` ou `R` (direções do mundo −y, +y, +x, −x), a 0,6 m da outra ponta no primeiro quadro e na altura dela. Com `lo` ou `hi` (por exemplo `Flo`), fica junto ao chão ou a 1,95 m. Postes à frente ou atrás ficam um pouco mais abertos, para a faixa passar ao lado do corpo.
    
    Exemplos: `band-hR-B` (presa atrás, na mão direita), `band-fL-hL` + `band-fL-hR` (faixa no pé esquerdo, pontas nas mãos), `band-aL-F` (tornozelo até um poste à frente);
  - `heldball`: bola segurada entre as palmas. O raio sai da distância entre as palmas no primeiro quadro (menos 3,5 cm), entre 8 e 30 cm, então os braços definem o tamanho da bola;
  - `ballfeet`, `ballarms`, `ballhands`, `ballback`: bola suíça de 55 cm no chão, sob os pés, os antebraços, as mãos ou a parte alta das costas. Um `L` ou `R` no fim (`ballfeetR`) escolhe um lado só. A cada quadro, a bola fica sob essa parte, rolada para fora, na linha que vem da pelve, só o bastante para não entrar no corpo (assim ela tangencia uma perna inclinada). Com `ballhands`, a bola fica parada onde estava no primeiro quadro. A parte apoiada precisa estar a uns 50–55 cm do chão no movimento. Mãos ou antebraços apoiados podem ter uma caixa de `ground` na altura do topo da bola, que o build usa para plantar o contato e que não é desenhada. As mãos devem ficar perto da linha do meio (braço aduzido), porque a bola é redonda. O log `BALL <id> <tipo> float <x> pen <y>` mostra a maior folga e a maior interpenetração do vídeo, e `BALL_DEBUG=1` lista os quadros com folga acima de 2 cm.
  - `stick`: bastão de 1,05 m passando pelas duas palmas, centrado entre elas. Variações:
    - `stick-<a>-<b>`: centrado entre duas pontas quaisquer, com os mesmos códigos da faixa e mais `eL`/`eR` (logo atrás do cotovelo, para o bastão preso na dobra dos cotovelos, atrás das costas);
    - `stickend-<a>-<b>`: a ponta do bastão fica na mão `a` e ele passa pela `b`, como na abdução ou na flexão assistida, em que a mão do braço trabalhado segura a ponta;
    - `stickfloor-<a>[-<b>]`: a ponta fica plantada no chão, sob a mão ou as mãos do primeiro quadro, e o bastão inclina acompanhando as mãos (alongamento com as mãos no topo do bastão, apoio para equilíbrio);
  - `towel-<a>-<b>`: toalha entre duas pontas, com os códigos da faixa (por exemplo `towel-fL-hL` + `towel-fL-hR`, toalha passada pelo pé);
  - `wobble`, `board`, `bosu`: almofada de equilíbrio, disco de equilíbrio ou BOSU sob os pés. O movimento leva uma caixa de `ground` sob os pés, com a altura do topo (7, 9 e 19 cm), e o acessório é desenhado no lugar da caixa, com o diâmetro dela;
  - `line`: fita no chão, atravessada no meio do caminho que a pelve percorre (saltos para a frente e para trás sobre a linha);
  - `marks`: marcas redondas no chão onde um pé pousa longe de onde começou (tocar alvos no chão);
  - `ladder-<cm>`: escada de agilidade no chão, ao longo do caminho da pelve, com degraus a cada `<cm>` e o primeiro pé no meio de um quadrado. Com `walk`, o deslocamento do vídeo precisa ser múltiplo do quadrado do piso (60 cm) e do degrau, para emendar (por exemplo, 1,2 m com degraus de 40 cm);
  - `walker`: andador parado, com as manoplas nas mãos do primeiro quadro em que elas ficam 20 cm à frente da pelve. Para as mãos ficarem nas manoplas enquanto o corpo agacha, use uma caixa de `ground` na altura delas e `touch: ["hand:arm"]` (o andador esconde a caixa);
  - `walkergo`: andador que acompanha as mãos a cada quadro (marcha com andador);
  - `caneL`, `caneR`: bengala da palma até o chão, acompanhando a mão;
  - `bedfit`: cama sob a pelve da primeira pose (levantar da beira da cama);
  - `chairbehind`: cadeira logo atrás de quem está em pé (miniagachamento em direção à cadeira);
  - `throw-<quem>-<alvo>-<t0>_<t1>[-<t0>_<t1>...]`: bola que sai das mãos (`h`) ou do pé (`fL`/`fR`, no chão à frente dele) entre `t0` e `t1` (frações do vídeo), vai até o alvo e volta. Alvos: `wall`, `wallL`, `wallR` (parede a 0,8 m), `floor` (quique no meio do caminho), `floorx` (quique alternando os lados) e `up` (lançamento de 55 cm). As frações saem dos tempos das poses: cada pose dura `beat`, mais o seu `hold`;
  - `waistball`: bola passada ao redor da cintura, na mão direita na primeira metade e na esquerda na segunda;
  - `pball-<tamanho>-<parte>[0]`: bola pequena no chão sob uma parte (`v`: bola de 22 cm, `t`: bolinha de tênis; partes `hL`/`hR`, `fL`/`fR`, `cL`/`cR` panturrilha, `kL`/`kR` atrás do joelho). Com `0` no fim, fica parada onde estava no primeiro quadro;
  - `wallpress-<ponta>-<direção>`: bola entre uma mão ou um pé e uma parede além dela (`F`, `B`, `L`, `R`), na distância máxima que a ponta alcança;
  - `bosuflat`: BOSU com a cúpula para baixo (plataforma em cima), no lugar da caixa de `ground`;
  - `pillow`: cada caixa de `ground` vira uma pilha de travesseiros, ou uma mesa com travesseiro em cima quando passa de 45 cm. Sob a cabeça, flexione um pouco o pescoço (`neck [14]` para 6 cm), senão a cabeça levanta o corpo inteiro;
  - `kneepillow`: travesseiro dobrado entre os joelhos;
  - `pulley`: roldana acima e atrás da cabeça, com a corda de uma mão à outra passando por ela;
  - `chairbox`: cada caixa de `ground` vira o assento de uma cadeira, com o encosto do lado oposto à pelve (mergulho de tríceps, calcanhar no assento da frente, flexão inclinada). Com `swissseat`, a caixa sob a pelve não é desenhada (quiques na bola).
- **Paredes e câmera:** as paredes dos acessórios ficam na frente ou ao lado do corpo. Escolha uma vista que não fique atrás delas (por exemplo `side`, e não `front3q`, com a parede à frente).
- **`move`** (opcional, em `jobs.json`): o movimento a tocar, quando o vídeo reaproveita o de outro job com acessórios diferentes (por exemplo, a marcha sentada na bola suíça usa `chair-march`).
- **Paleta:** `MANNEQUIN_PALETTE`. As opções são `areia` (padrão), `cinza`, `ardosia`, `salvia` e `azul`.

## Limites do manequim

- Sem dedos (a mão é uma luva) e sem rosto.
- Sem clavícula: o encolher de ombros é `arm.pos`.
- A coluna é um osso só.
- O contato automático (mão ou pé que fica preso) só existe com o chão e com as caixas do `ground`. Mão no encosto ou na parede funciona porque o acessório é posicionado onde a mão está, e não porque a mão se prende ao acessório.
- O aterramento é geométrico: o ponto mais baixo encosta na superfície. Uma pose pode "apoiar" na cabeça e nos pés com a pelve no ar, e as linhas `KEY` do build servem para pegar isso.

## Licença

O desk-break é MIT. Ao distribuir vídeos ou o modelo, inclua o aviso de copyright do `build/desk-break/LICENSE`, por exemplo na tela de licenças do app.
