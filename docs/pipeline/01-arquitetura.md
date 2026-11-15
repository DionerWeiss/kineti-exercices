# 01 · Arquitetura

## Visão geral

```
research/pocketphysio/exercicios.json        (catálogo PP: id, nome_pt, descricao_pt, posicao…)
            │  escolha dos exercícios que o rig consegue fazer
            ▼
tool/mannequin/jobs.json  ──────────────┐   1 job = 1 vídeo: lib, view, props, pocketphysio[], move?
tool/mannequin/kineti_moves.json         │   poses-chave escritas por nós (ids kineti-*)
tool/mannequin/deskbreak_moves.json      │   os 159 movimentos do desk-break, copiados para cá e editáveis
            │                            │
            ▼  mannequin.py build ids    │
kineti_builder.py (Blender)              │   poses → curvas; aterra; prende pés/mãos; "ground" e "touch"
            │  <out>/kineti_sub/exercises.blend
            ▼  mannequin.py sync ids     │
E:\mannequin\avatar_man\exercises_final.blend   lib final: rig + avatar v9 + mannequin_ref + todas as actions
            │                            │
            ▼  mannequin.py render ids   ▼
render_mannequin.py (Blender, por job):
   reground → clear_limbs → reground → plant (mãos) → unclip_arms   (plant_hands.py)
   acessórios, câmera, grip das mãos, Eevee → PNGs → ffmpeg → MP4 1920×1080 30 fps
   QA=1: qa_pose.py (camada 1) + motion_qa.py (dados da camada 2)
            │
            ├─► motion_review.py, video_qa.py   camada 2 (movimento, vídeo)
            ├─► pp_compare.py                   camada 3 (lado a lado com o PP)
            ├─► review.py → review.csv          junta tudo + notas de revisão
            ├─► tool/puppet2d (export_joints → drive_puppet/drive_front → render.mjs)   Lottie 2D
            └─► compare_catalog.py → E:\mannequin\catalogo (PP × manequim × Lottie × 3D) → app /catalogo
```

## Peças

### Rig e corpo
- **Rig do desk-break:** 15 grupos de osso (`hips spine neck arm elbow hand leg knee foot`, com lados L/R). Sem dedos, sem clavícula e com a coluna em um osso só.
- **Manequim:** o corpo original do desk-break. Fica oculto na lib do avatar como `mannequin_ref`, para servir de referência de aterramento (`add_ref.py`).
- **Avatar v9:** homem low-poly (camisa azul Kineti com gola em V, short preto, tênis escuro, cabelo `SM_Char_Avatar_Hair`). Ajustado ao mesmo rig por `avatar/fit_avatar.py` (skinning dos ossos Mixamo somado nos 15 grupos), então os movimentos não precisam de retarget. Traz shape keys `grip_L`/`grip_R` para fechar as mãos.

### Movimentos e construtor
- Um movimento é uma lista de poses-chave em graus por osso, com `beat` (segundos por transição), `hold`, `pos` (deslocamento da pelve), `touch` e `ground` ([03](03-movimentos.md)).
- `kineti_builder.py` é um fork do `build_library.py` do desk-break. Sem `ground`, gera as mesmas curvas que o original. Ele:
  - interpola as poses;
  - aterra cada quadro (o ponto mais baixo toca a superfície);
  - prende pés e mãos que pousam (IK) e solta quando a pose os levanta;
  - resolve `touch` (ângulo que faz o pé ou a mão tocar a superfície);
  - aceita um campo de alturas `ground` (degrau, cadeira, cama, caixa invisível sob a bola).
- `mannequin.py build ids` constrói só os movimentos pedidos em `<out>/kineti_sub` (kineti) e `desk_sub` (desk-break). `sync ids` copia as actions para a lib do avatar (`sync_actions.py`).

### Render (`render_mannequin.py`, dentro do Blender)
1. Carrega a action do job na lib.
2. Com o avatar (`AVATAR=1`), roda `plant_hands.py`:
   - `reground`: em cada quadro, põe no apoio as partes do avatar que o manequim apoia (o tênis do avatar desce 1,2 cm abaixo do pé do manequim);
   - `clear_limbs`: braço ou perna que atravessa o chão sobe (perna por IK com o pé parado, braço girando no ombro);
   - `reground` de novo;
   - `plant`: mão espalmada no chão, nas caixas de `ground`, na mesa ou no encosto. Mão de apoio = perto do chão, antebraço em pé, cotovelo fora do chão (peso suavizado em 21 quadros). Inclina o corpo em volta dos outros apoios (`tilt`) ou gira o braço no ombro (`swing`);
   - `unclip_arms`: antebraço ou mão afundados no tronco, pernas ou cabeça são empurrados para fora pelo ombro.
3. Monta os acessórios (`props`), o colchonete e a câmera (`view`, `frame`), e aplica o grip (punho fechado em corrida, `relax 0.3 × (1 − apoio)` nos demais casos).
4. Renderiza no Eevee e monta o MP4: 0,5 s parado na primeira pose, depois a action repetida até ter pelo menos 2 repetições.
5. Com `QA=1`, mede a cena pronta (camada 1) e grava os dados de movimento (camada 2).

### Revisão
Quatro camadas, explicadas em [06](06-revisao.md):
1. pose e contatos (automática);
2. movimento e vídeo (automática);
3. comparação com o PocketPhysio (agente ou pessoa);
4. revisão visual (agente ou pessoa).

O resultado vai para `review.csv`.

### Lottie 2D
O boneco recortado do Dinh, recolorido em azul Kineti, dirigido pelas juntas 3D do mesmo movimento. Há uma vista lateral e uma frontal, e uma vista de cima para quem está deitado ([09](09-lottie.md)).

### Catálogo e app
- `compare_catalog.py` gera uma página local que põe lado a lado PP, manequim, Lottie e 3D, com os vereditos.
- O app Next.js (raiz do repo) tem a revisão por upload (`/exercicios`) e uma cópia do catálogo (`/catalogo`) com notas salvas no Supabase ([10](10-catalogo-e-app.md)).

## Histórico das abordagens (por que este pipeline)

| Data | Abordagem | Resultado |
|---|---|---|
| 06/11 | Lottie stick figure, 3D MPFB dirigido pelo rig, mocap MediaPipe, cartoonização de vídeo | Rejeitadas ("estranho") |
| 06/11 | Avatar ilustrado D + imagem Gemini + Veo (Vertex) | Abandonada em 07/11 (sem Gemini) |
| 07/11 | Mulher MPFB com mocap Mixamo real | Rejeitada |
| 07/11 | Manequim de madeira do desk-break, repintado e com a marca Kineti | Adotado. 688 vídeos em 08/11, em `E:\mannequin\videos` |
| 10/11 | Avatar estilo vetor (regata laranja, toon) | Não seguiu |
| 10–12/11 | Homem low-poly no mesmo rig. v9 (com cabelo) aprovado em 12/11 | **Render 3D atual** |
| 10–14/11 | Boneco Lottie 2D dirigido pelo rig. Aprovado em 14/11 | **Lottie atual** |
