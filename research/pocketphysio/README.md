# PocketPhysio: catálogo analisado

Os 1.756 exercícios da API do PocketPhysio (1.581 publicados), analisados um a um. Para cada um há uma descrição original em PT-BR, o esforço para reproduzir em três pipelines e a dificuldade de entender e de comunicar o movimento.

- `exercicios.json`: tudo, inclusive as características extraídas (`caracteristicas`) e os motivos de cada nota.
- `exercicios.csv`: a mesma tabela, para planilha (UTF-8 com BOM).
- Os vídeos não foram baixados; `video` aponta para o S3 deles.

## Como foi feito

1. `tool/pocketphysio/analyze.py`: o Gemini 3 Flash (Vertex) assiste cada vídeo, com a narração, e devolve características objetivas (posição, fases, segmentos, acessórios, interação com objeto, amplitude...), a descrição e duas notas de 0 a 10.
   - Vídeos de mais de ~15 MB descem e vão em 360p na própria requisição.
   - Sem vídeo, a análise usa imagem e texto (`fonte = imagem+texto`, 33) ou só texto (`fonte = texto`, 147, quase todos não publicados).
2. `tool/pocketphysio/match_library.py`: compara cada um com os 59 do Kineti (`catalog.json`) e com os 435 do desk-break, e marca `identico`, `variacao` ou `novo`.
3. `tool/pocketphysio/score.py`: calcula o esforço com uma rubrica fixa, sem LLM. A rubrica pode mudar e ser recalculada sem rever os vídeos.

## Colunas

| coluna | o que é |
|---|---|
| `entendimento` | 0–10: dificuldade de entender e especificar o movimento a partir do vídeo e do texto |
| `comunicabilidade` | 0–10: dificuldade de o paciente entender só pela animação muda (isometria, respiração e rosto ficam altos) |
| `esforco_lottie` | 0–10 no rig Lottie atual (`figure3d` + builders) |
| `esforco_blender` | 0–10 no personagem 3D atual, que reaproveita a cinemática do Lottie e soma o custo do 3D (colisões, dedos, rosto, acessórios a modelar) |
| `esforco_manequim` | 0–10 no manequim desk-break + `build/kineti_mannequin/render_v2.py` (poses em JSON, chão automático; sem dedos, sem rosto, sem clavícula, contatos só com o chão) |
| `motivos_*` | o que mais pesou na nota |
| `relacao_kineti` / `relacao_deskbreak` | se já existe pronto: `identico` multiplica o esforço por 0,2; `variacao` por 0,6 (Kineti) ou 0,5 (desk-break) |

Escala: os pontos somados passam por `10·(1−e^(−p/8))`, então só o que exige rig novo chega a 8–10. Referência: no Lottie, "sentar e levantar" ou "ponte" ficam em 1–3, decúbito lateral e quatro apoios em 4–5, e dedos ou rosto em 7–8.

## Distribuição (publicados)

| nota | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| esforco_lottie | 30 | 189 | 355 | 306 | 321 | 202 | 127 | 46 | 5 | 0 | 0 |
| esforco_blender | 2 | 80 | 173 | 218 | 310 | 298 | 243 | 164 | 82 | 11 | 0 |
| esforco_manequim | 81 | 366 | 298 | 264 | 210 | 113 | 89 | 74 | 71 | 15 | 0 |
| entendimento | 13 | 1239 | 312 | 12 | 4 | 0 | 0 | 1 | 0 | 0 | 0 |
| comunicabilidade | 3 | 311 | 871 | 177 | 91 | 36 | 25 | 26 | 33 | 8 | 0 |

Publicados com nota até 3: Lottie 880, Blender 473, manequim 1009.

## O que trava cada pipeline

- **Manequim:** dedos e rosto (178, inviáveis sem trocar o personagem), mão presa num apoio fora do chão (IK nova no `render_v2`), mão no próprio corpo (sem colisão), escápula e coluna segmentada. Acessórios que mais faltam no `render_v2`: mesa, faixa elástica, bola suíça, travesseiro, degrau e bastão.
- **Lottie e Blender:** poses novas (ajoelhado, semiajoelhado, sentado no chão), transições chão↔em pé, objetos dinâmicos ou deformáveis e segunda pessoa. No Blender pesam também dedos (não cobertos) e rosto.

## Primeiros da fila: 202 publicados idênticos a um exercício do desk-break

| manequim | nome | desk-break |
|---|---|---|
| 0 | Flexão e extensão de cotovelo sentado | `chair-biceps-curl` |
| 0 | Panturrilha unilateral em pé | `single-calf-raise-supported` |
| 0 | Elevação de calcanhares em pé | `calf-raise` |
| 0 | Elevação da perna estendida (SLR) em decúbito dorsal | `straight-leg-raise` |
| 0 | Elevação de perna estendida (SLR) | `straight-leg-raise` |
| 0 | Elevação de perna esticada (SLR) | `straight-leg-raise` |
| 0 | Deslizamento de calcanhar em supino | `heel-slides` |
| 0 | Deslizamento de calcanhar em supino | `heel-slides` |
| 0 | Circundução de punhos sentado | `chair-wrist-circles` |
| 0 | Circundução de punhos sentado | `chair-wrist-circles` |
| 0 | Flexão e extensão de pescoço | `neck-nod` |
| 0 | Flexão de joelho em decúbito prono | `prone-heel-to-seat` |
| 0 | Alongamento de adutores de quadril em supino | `reclined-butterfly` |
| 0 | Elevação de braços deitado (Flexão de ombro) | `lying-arm-reach` |
| 0 | Flexão de ombro em supino | `lying-arm-reach` |
| 0 | Flexão de ombro a 90 graus em supino | `lying-arm-reach` |
| 0 | Agachamento básico | `sit-back-squat` |
| 0 | Agachamento livre com braços à frente | `mini-squat` |
| 0 | Marcha estacionária com balanço de braços | `march-in-place` |
| 0 | Marcha estacionária | `march-in-place` |
| 0 | Caminhada rápida estacionária com balanço de braços | `march-in-place` |
| 0 | Rotação cervical em pé | `neck-rotation` |
| 0 | Marcha estacionária | `march-in-place` |
| 0 | Bicicleta no ar | `slow-bicycle-legs` |
| 0 | Marcha estacionária com braços | `march-in-place` |
| 0 | Socos frontais alternados | `punches` |
| 0 | Deslizamento de calcanhar em supino | `heel-slides` |
| 0 | Alongamento de posterior de coxa em supino | `lying-hamstring-stretch` |
| 0 | Elevação da perna estendida em decúbito dorsal | `straight-leg-raise` |
| 0 | Circundução de tornozelo sentado | `chair-ankle-circles` |
| 0 | Equilíbrio unipodal | `balance-single-leg-stand` |
| 0 | Marcha estacionária com apoio | `balance-slow-march` |
| 0 | Flexão de pernas alternada em decúbito dorsal | `heel-slides` |
| 0 | Rotação de tornozelo | `ankle-circles` |
| 0 | Equilíbrio unipodal com rotação cervical | `single-leg-head-turns` |
| 0 | Inclinação lateral da cabeça sentado | `chair-neck-tilt` |
| 0 | Abdução de ombro excêntrica com braço elevado | `lateral-raise` |
| 0 | Equilíbrio em uma perna só | `balance-knee-raise-hold` |
| 0 | Equilíbrio em Tandem (Um pé à frente do outro) | `heel-to-toe-stand` |
| 0 | Extensão de quadril em quatro apoios (Coice) | `donkey-kick` |

(lista completa: filtre `relacao_deskbreak = identico` no CSV)

## Ressalvas

- As características vêm de um modelo que assistiu ao vídeo; as notas de esforço são uma estimativa por rubrica. Use para priorizar, não como orçamento.
- `variacao` em relação ao Kineti está generosa (610 casos para uma biblioteca de 59), então o esforço Lottie/Blender desses tende a estar subestimado.
- Material de terceiros: os vídeos e títulos originais são do PocketPhysio/VirtueLife. As descrições em PT-BR foram escritas do zero.

## Recalcular

`raw/` guarda o que veio da API (`api_exercises.json`, 2026-11-07), a análise do Gemini e as duas comparações. Para mudar a rubrica, edite `score.py` e rode:

```bash
python3 tool/pocketphysio/score.py research/pocketphysio/raw/api_exercises.json research/pocketphysio/raw/analise.jsonl research/pocketphysio \
  --kineti research/pocketphysio/raw/match_kineti.jsonl --deskbreak research/pocketphysio/raw/match_deskbreak.jsonl
```
