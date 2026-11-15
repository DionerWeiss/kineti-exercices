#!/bin/bash
# render_part.sh NN: render + QA of lote NN only (no compare)
N=$1; F=/mnt/e/mannequin/avatar_man/final; O=/mnt/e/mannequin/avatar_man/out; IDS=$F/lotes/lote_$N.txt
cd /home/dioner/projects/kineti/animated_exercices
export MANNEQUIN_AVATAR=/mnt/e/mannequin/avatar_man/exercises_final.blend MANNEQUIN_OUT=$F MANNEQUIN_RES=1920x1080 \
       MANNEQUIN_VIDEOS=$O/videos_final MANNEQUIN_DROP_FRAMES=1 QA=1 EEVEE_SAMPLES=16
echo "== lote $N start $(date +%T)"
python3 tool/mannequin/mannequin.py render $(cat $IDS) 2>&1 | grep -E "^  QA |Error|ERROR|Traceback|WARNING" | tail -80
echo "== render done $(date +%T)"
