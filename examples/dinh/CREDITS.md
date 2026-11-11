# Créditos · lotes Dinh (azul Kineti)

Animação original: **Dinh Bui Xuan** em [LottieFiles](https://lottiefiles.com/buixuandinh).

Alteração nestes lotes: só a cor da regata (ou do tronco colorido equivalente) para o azul do Kineti (`#2563EB` / `#1E40AF`). Keyframes, camadas e duração são os do arquivo original.

## Lote 1 · mais simples

| Arquivo | Página no LottieFiles |
| --- | --- |
| `forearm_stretch.json` | [Forearm Stretch](https://lottiefiles.com/free-animation/forearm-stretch-exercise-for-tired-of-cancer-bv-JPM0xvI0po) |
| `shoulder_stretch.json` | [Shoulder Stretch](https://lottiefiles.com/free-animation/shoulder-stretch-EN29iDeQQg) |
| `cobra.json` | [Cobras](https://lottiefiles.com/free-animation/cobras-w0bL4N81bN) |
| `squat_reach.json` | [Squat Reach](https://lottiefiles.com/free-animation/squat-reach-Dp1w6IjOlQ) |
| `reverse_crunches.json` | [Reverse Crunches](https://lottiefiles.com/free-animation/reverse-crunches-79P2FMTS7Z) |
| `step_up_on_chair.json` | [Step Up on Chair](https://lottiefiles.com/free-animation/step-up-on-chair-zcvfCJwhkF) |

## Lote 2 · restante

| Arquivo | Página no LottieFiles |
| --- | --- |
| `walking_hip_opener.json` | [Walking Hip Opener](https://lottiefiles.com/free-animation/walking-hip-opener-standard-yJtiYrJwk0) |
| `lunge.json` | [Lunge](https://lottiefiles.com/free-animation/lunge-Ls3pMlE0a0) |
| `military_push_ups.json` | [Military Push Ups](https://lottiefiles.com/free-animation/military-push-ups-sFmjfnsBQ9) |
| `wide_arm_push_up.json` | [Wide Arm Push Up](https://lottiefiles.com/free-animation/wide-arm-push-up-KD96z4DT4Y) |
| `staggered_push_ups.json` | [Staggered Push Ups](https://lottiefiles.com/free-animation/staggered-push-ups-zgWfOIvx3C) |
| `t_plank.json` | [T Plank](https://lottiefiles.com/free-animation/t-plank-exercise-g5qVU6RPYY) |
| `press_up_toe_tap.json` | [Press Up Toe Tap](https://lottiefiles.com/free-animation/press-up-postion-toe-tap-KunqnEdK18) |
| `punches.json` | [Punches](https://lottiefiles.com/free-animation/punches-DK1guXUDFv) |
| `frog_press.json` | [Frog Press](https://lottiefiles.com/free-animation/frog-press-LqkyGCKGpu) |
| `seated_abs_circles.json` | [Seated Abs Circles](https://lottiefiles.com/free-animation/seated-abs-circles-kgOH7mJGKJ) |
| `squat_kicks.json` | [Squat Kicks](https://lottiefiles.com/free-animation/squat-kicks-2UaqzO5zfR) |
| `jumping_squats.json` | [Jumping Squats](https://lottiefiles.com/free-animation/jumping-squats-9hzVV8Ohi6) |
| `jumping_jack.json` | [Jumping Jack](https://lottiefiles.com/free-animation/jumping-jack-Q3NN7cRkd4) |
| `split_jump.json` | [Split Jump](https://lottiefiles.com/free-animation/split-jump-exercise-AHHpx1bumx) |
| `box_jump.json` | [Box Jump](https://lottiefiles.com/free-animation/box-jump-exercise-dbDFpRb3Go) |
| `burpee_and_jump.json` | [Burpee and Jump](https://lottiefiles.com/free-animation/burpee-and-jump-exercise-gCOcxxnr1X) |
| `inchworm.json` | [Inchworm](https://lottiefiles.com/free-animation/inchworm-oMKbWGAaDD) |
| `clean_and_press.json` | [Clean and Press](https://lottiefiles.com/free-animation/double-arm-clean-and-press-barbell-wpiqpl8RKn) |

Fora destes lotes (não são exercício, ou são duplicata): fingerprint, QR, troféu, usage data, e as variantes `t-plank-excercise`, `squat-kick`, `seated-abs-circle`.

## Lote 3 · puppet clínico

O boneco do [Split Jump](https://lottiefiles.com/free-animation/split-jump-exercise-AHHpx1bumx) é dirigido pelos joints 3D do manequim (`drive_puppet.py --kineti`). Fonte do puppet: `E:\mannequin\puppet2d\scripts\split-jump-dinh.json`. Joints: `E:\mannequin\puppet2d\batch_test\joints_desk.json`.

| Arquivo | Ação no manequim |
| --- | --- |
| `puppet/ankle_pumps.json` | `floor-ankle-pumps` |
| `puppet/heel_slides.json` | `heel-slides` |
| `puppet/bridge.json` | `glute-bridge` |

`sit_to_stand` ainda não entra: falta o Blender no PATH para exportar `kineti-sit-to-stand` de `E:\mannequin\kineti_lib\exercises.blend`.

Para regenerar o lote 3:

```bash
cd /mnt/e/mannequin/puppet2d/scripts
.venv/bin/python -I drive_puppet.py split-jump-dinh.json ../batch_test/joints_desk.json floor-ankle-pumps \
  /home/dioner/projects/kineti/animated_exercices/examples/dinh/puppet/ankle_pumps.json --kineti
```

Os JSON em `src/` são a fonte baixada do LottieFiles (formato embutido no `.lottie` público). A licença gratuita (Lottie Simple License) permite usar e modificar no produto; o JSON cru deste lote não é redistribuído como pacote de animações.

Para regenerar as versões azuis (lotes 1–2) a partir de `src/`:

```bash
python3 examples/dinh/recolor.py
```
