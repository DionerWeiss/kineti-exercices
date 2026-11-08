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
- **Vistas** (`DIRS` em `render_mannequin.py`): `side`, `front`, `side3q`, `front3q`, `rside3q`, `back3q`, `top3q` e `floor`. A `floor` é de lado e alta, para quem está deitado. Com o corpo deitado ao longo do eixo X, as vistas giram 90°, então "lado" continua sendo de través.
- **Colchonete:** cobre a área ocupada pelo corpo durante todo o movimento. Só aparece sem `chair`, `ball`, `support` ou `wall`.
- **Acessórios:**
  - `chair`: cadeira, com o manequim sentado;
  - `support`: encosto de cadeira à frente, na altura das mãos;
  - `side`: cadeira ao lado, com a mão que está mais afastada do corpo no encosto;
  - `wall`: parede na frente das mãos;
  - `roll`: rolo sob o joelho;
  - `ball`: bola entre os joelhos, que achata;
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
