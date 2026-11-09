# Vídeos 3D dos exercícios

Os vídeos usam o personagem 3D do Kineti (Blender), movido pela mesma cinemática das animações Lottie. Cada exercício sai do seu builder de sempre, então movimento, câmera e enquadramento são os mesmos do Lottie.

```bash
python3 tool/render_3d.py bridge mini_squat         # videos/<área>/<slug>.mp4
python3 tool/render_3d.py --still bed_rolling       # 4 quadros em build/3d/<slug>/, para conferir
python3 tool/render_3d.py --all                     # todos, menos os close-ups de mão
```

## Como funciona

1. **`export_scene.py`** (WSL) constrói a cena com o builder do Lottie, com as mesmas verificações, e grava em `build/3d/<slug>/scene.json`:
   - as articulações e as bases da pelve e do tórax, quadro a quadro;
   - a câmera;
   - os acessórios: caixas, barras e painéis do rig 3D, linhas e polígonos de perfil do rig 2D, as faixas elásticas, e os objetos desenhados em tela (bola, halteres, tornozeleira), reconstruídos a partir das mesmas articulações;
   - os ossos da parte que trabalha, os mesmos do destaque laranja do Lottie.

   Nas cenas de perfil, o 3D é reconstruído a partir da pose, porque o rig 2D põe cada lado do corpo numa profundidade fixa.
2. **`render_scene.py`** (Blender, sem interface) abre o personagem e monta o cenário. A cadeira de perfil vira cadeira 3D, e parede e degrau viram blocos. Depois posiciona o esqueleto quadro a quadro e renderiza PNGs:
   - **Orientação:** pelve e tórax seguem as bases do rig, e a coluna segue a linha da coluna do rig.
   - **Clavículas:** seguem os ombros do rig, então encolher e retrair os ombros aparece.
   - **Braços e pernas:** usam IK de dois ossos com as medidas do personagem, mirando nas mãos e tornozelos do rig. Assim os pés ficam no chão e as mãos no apoio.
   - **Cabeça:** acompanha a flexão do tronco, mas só um terço da torção.
   - **Mão sobre uma superfície:** o pulso sobe o bastante para a palma pousar no apoio, a mão deita e os dedos esticam ao longo dela, em vez de ficarem na pose de descanso e entrarem no colchão.
   - **Braços cruzados:** a palma vai para a frente do ombro oposto e o cotovelo aponta para fora, para o braço não entrar na camiseta.
   - **Bola, halteres e tornozeleira:** esfera achatada entre os joelhos, haltere na palma (barra e duas anilhas) e anel no tornozelo, cada um animado quadro a quadro.
3. **`tool/render_3d.py`** junta as duas etapas e monta o MP4 com `ffmpeg`. A saturação sobe 18%, em RGB e preservando a luminância, para o fundo não mudar de tom.

## Ajustes do personagem

- **Braço e antebraço:** ficam com 88% do comprimento do modelo (`--arm`), escalados só no eixo do osso. A mão não muda.
- **Saturação:** é a constante `SATURATION` em `render_3d.py`.
- **Faixa elástica:** laranja chapado (#FF6D00, a terciária do app).

## Requisitos

- Blender 5.3. Por padrão é usado `/mnt/e/tools/blender-5.3.0/blender.exe`; mude com `KINETI_BLENDER`.
- O personagem `kineti_character.blend` (volume, luz de três pontos, sem contorno de ilustração). Por padrão fica em `C:\Users\Dioner\Documents\kineti_exercises\`; mude com `KINETI_CHARACTER`. O arquivo referencia a estampa da camiseta nessa mesma pasta. O ilustrado continua disponível como `kineti_character_illustrated.blend`.
- `ffmpeg` no WSL.

## Ainda não coberto

- Os close-ups de mão (lote 4) têm desenho próprio e precisam de uma cena 3D com os dedos do personagem.
- O rolo de toalha do arco curto é um cilindro sob o joelho. O painel desenhado pelo builder é ignorado para não virar uma tábua ao lado do rolo.
