# 09 · Lottie 2D

O boneco recortado "Split Jump" do Dinh Bui Xuan (LottieFiles, Lottie Simple License), recolorido em azul Kineti e dirigido quadro a quadro pelas juntas 3D do mesmo movimento do render. As correções de movimento do 3D valem automaticamente para o Lottie, depois que ele é regerado. Saída em Lottie JSON (76–240 KB por exercício), que o kineti_app toca de forma nativa.

## Peças (`tool/puppet2d/`)

| Arquivo | Função |
|---|---|
| `export_joints.py` | Roda no Blender sobre uma lib. Exporta cabeça e cauda dos ossos por quadro, mais `_low` (ponto mais baixo de cada mão e pé), `_palm`, `_tip`, `rest` e `_ground` do movimento |
| `drive_puppet.py` | Boneco lateral: projeção sagital, FK no ar e IK perto do chão, pés ancorados, mãos (aberta, punho, espalmada), ~100 props |
| `drive_front.py` + `front_puppet.json` | Boneco frontal (do "Jumping Jack" do Dinh, reestilizado como o mesmo homem). Mesma linha de comando. Trata o escorço |
| `top_view.py` | Gira as juntas de um movimento deitado para a vista de cima (`top`; `--side` para deitado de lado, `sidetop`) |
| `pick_view.py` | Decide `front` ou `side` por action, pelo espalhamento do movimento nos eixos do próprio corpo |
| `gen_jobs.sh` | Gera um Lottie por **job** (`<job> <action> <front\|side\|top\|sidetop> [flags]` por linha) |
| `gen.sh` | O mesmo por action, só com o lateral |
| `render.mjs` | lottie-web em Chromium headless → MP4 (1080 px, 60 fps, ≥ 2 ciclos, ≥ 10 s) |
| `snap.mjs` | Quadros isolados em PNG, para conferir de perto |
| `lottie_despike.py` | Remove tremidas de um quadro (um key que sai e volta com a pose parada) |

## Gerar

```bash
# 1. juntas, de uma CÓPIA da lib final (o render pode estar usando a original)
cp /mnt/e/mannequin/avatar_man/exercises_final.blend /mnt/e/mannequin/puppet2d/final/lib_snapshot.blend
cp tool/puppet2d/export_joints.py /mnt/e/mannequin/puppet2d/scripts/      # a versão do repo é a atual
/mnt/e/tools/blender-5.3.0/blender.exe -b 'E:\mannequin\puppet2d\final\lib_snapshot.blend' \
   --python 'E:\mannequin\puppet2d\scripts\export_joints.py' -- 'E:\mannequin\puppet2d\final\joints.json' <actions…>
# 2. vista
uv run -q --no-project --with numpy python3 -I tool/puppet2d/pick_view.py joints.json <actions…> --json
# 3. lista "<job> <action> <view> [--props=… --hands=… --walk]" e geração
tool/puppet2d/gen_jobs.sh joints.json /mnt/e/mannequin/puppet2d/final lista.txt
# 4. piscadas (deve dar 0)
uv run -q --no-project --with numpy python3 tool/mannequin/ops/blink.py /mnt/e/mannequin/puppet2d/final/*.mp4
```

- O Blender é o do Windows: passe caminhos do Windows e copie o script para o E:.
- Um job usa a action do campo `move` do job, ou o próprio id. Os `props` do job viram `--props=`, `walk` vira `--walk` e `throw` não é desenhado.
- `--hands=auto` dá punho em corrida, marcha e soco, e mão aberta nos outros casos.
- Até 3 jobs em paralelo, se um render 3D estiver usando a CPU.

Saída por job: `<job>.json`, `<job>.mp4`, `strips/<job>.png` e `qa/<job>.json|log`. Entrega: `final/manifest.json` (vista, flags, números do QA, status `ok` ou `limitação` com o motivo), `sheet_lote_NN.png` e `move_bugs.txt`.

## Revisão

Instruções completas: [agentes/lottie_all_brief.md](agentes/lottie_all_brief.md).

- Automático: piscadas = 0; flutuação ≤ 5 px; deslize ≤ 1,5 px/quadro; render sem falha; quadro sem corte; props pedidos desenhados.
- Visual: todo job marcado, mais 1 em 10, em tamanho real (mãos, props, contatos), comparando com o vídeo do PP.
- Bugs do movimento 3D vistos pelo boneco vão para `move_bugs.txt` (as mesmas juntas dirigem o 3D).

## O que o cliente cobrou e como foi resolvido

| Queixa | Solução |
|---|---|
| A mão aberta "não parece que faz parte do braço" | A mão começa exatamente nas bordas do punho, amostradas do contorno do antebraço |
| Corpo afunda ao trocar de perna; sapatos mal apoiados; vídeos curtos | Altura segue o quadril 3D; segunda passada de IK até a linha do chão; linha de chão por pé (perspectiva); sapato plano que vira na ponta quando o tornozelo sobe; ≥ 10 s |
| Perna do butt-kick com bug; boneco pula na ponta dos pés | Contato pelo `_low`; FK no ar e IK só perto do chão; pé de apoio principal com antecipação |
| Piscar | Era a volta do ângulo em ±180° interpolada como um giro completo. `np.unwrap` em toda trilha de rotação antes de gravar os keys |
| Mãos melhores, sem piscar, props | Mão desenhada, mão espalmada por IK no apoio, props |

Não use suavização global que solte contatos. A suavização gaussiana em loop (σ = 1,2 quadro) nas juntas é a única permitida.

## Estado (15/11)

- 679 Lotties: 576 ok e 103 com limitação. Vistas: 492 lado, 153 frente, 25 de cima, 9 lado-de-cima.
- Limitações do desenho 2D: escápula, coluna, queixo, giro de cabeça, círculos de tornozelo, escorço (membro apontando para a câmera), arremesso, postes de faixa à esquerda ou à direita.
- Os 84 exercícios alterados no fim foram regerados com os drivers novos. Os outros ~595 ainda são da versão anterior dos drivers. Regerar leva ~3 h, sem GPU.
- Os 9 close-ups de mão (`lib: hand`) não têm Lottie.
