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
- **`library_map.json`:** para cada um dos 59 exercícios da biblioteca Kineti, o vídeo do manequim que o substitui, ou `null` e o motivo (dedos, rosto, faixa elástica, mesa, cama, degrau, caminhada). No catálogo, ele aparece no campo `substitui`.
- **`texts_pt.json`:** nome, descrição, foco e área de cada vídeo, escritos à mão (`{slug: [nome, descrição, foco, área]}`). A descrição segue o que o vídeo mostra, e não o texto original do desk-break. Os movimentos Kineti que já estão na biblioteca usam os textos do `catalog.json` dela.
- **`kineti_moves.json`:** movimentos escritos por nós, no formato do desk-break (veja `build/desk-break/library/AUTHORING.md`). Os ids começam com `kineti-`.
- **Close-ups da mão** (`lib: "hand"`): a mão de madeira com dedos, no estilo do manequim, apoiada na mesa. `export_hand.py` exporta, quadro a quadro, a cinemática da mão do Lottie (`tool/build_library_hand_animations.py`), com as mesmas verificações. Depois `render_hand.py` monta segmentos, articulações, palma, mesa e câmera no Blender. São usados em punho, antebraço, abrir e fechar a mão e oposição do polegar.
- **`render_mannequin.py`:** roda dentro do Blender. Repinta o manequim, aplica a marca, monta o cenário e a câmera, e renderiza.
- **`build_lib.py`:** roda o `build_library.py` do desk-break num arquivo de movimentos e salva o `.blend`, que o original só grava para a biblioteca inteira.

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
  - `dumbbell`: halteres nas mãos.
- **Paleta:** `MANNEQUIN_PALETTE`. As opções são `areia` (padrão), `cinza`, `ardosia`, `salvia` e `azul`.

## Limites do manequim

- Sem dedos (a mão é uma luva) e sem rosto.
- Sem clavícula: o encolher de ombros é `arm.pos`.
- A coluna é um osso só.
- O contato automático (mão ou pé que fica preso) só existe com o chão. Mão no encosto ou na parede funciona porque o acessório é posicionado onde a mão está, e não porque a mão se prende ao acessório.

## Licença

O desk-break é MIT. Ao distribuir vídeos ou o modelo, inclua o aviso de copyright do `build/desk-break/LICENSE`, por exemplo na tela de licenças do app.
