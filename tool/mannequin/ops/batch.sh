#!/bin/bash
# batch.sh NN: render + QA + PP compare + review + contact sheet of lote NN (final/lotes/lote_NN.txt)
N=$1
F=/mnt/e/mannequin/avatar_man/final
O=/mnt/e/mannequin/avatar_man/out
IDS=$F/lotes/lote_$N.txt
cd /home/dioner/projects/kineti/animated_exercices
export MANNEQUIN_AVATAR=/mnt/e/mannequin/avatar_man/exercises_final.blend MANNEQUIN_OUT=$F MANNEQUIN_RES=1920x1080 \
       MANNEQUIN_VIDEOS=$O/videos_final MANNEQUIN_DROP_FRAMES=1 QA=1
echo "== lote $N start $(date +%T)"
python3 tool/mannequin/mannequin.py render $(cat $IDS) 2>&1 | grep -E "^  QA |Error|ERROR|Traceback|WARNING" | tail -80
echo "== render done $(date +%T)"
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py fetch $(cat $IDS) 2>&1 | tail -3
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py compare $(cat $IDS) 2>&1 | grep -E "Error|Traceback" | tail -5
echo "== compare done $(date +%T)"
cd tool/mannequin
python3 contact_sheet.py $O/videos_final $IDS $O/contact_lote_$N.png $F/qa 2>&1 | tail -1
python3 review.py $F $O/videos_final $IDS review_lote_$N.csv 2>&1 | tail -6
python3 review.py $F $O/videos_final > /dev/null 2>&1
echo "== lote $N end $(date +%T)"
