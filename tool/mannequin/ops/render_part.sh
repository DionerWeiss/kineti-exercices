#!/bin/bash
# render_part.sh NN: render + QA of lote NN only (no compare)
source "$(dirname "$0")/env.sh"
N=$1; IDS=$F/lotes/lote_$N.txt
cd $R
export MANNEQUIN_AVATAR=$LIB MANNEQUIN_OUT=$F MANNEQUIN_RES=1920x1080 \
       MANNEQUIN_VIDEOS=$VID MANNEQUIN_DROP_FRAMES=1 QA=1 EEVEE_SAMPLES=16
echo "== lote $N start $(date +%T)"
python3 tool/mannequin/mannequin.py render $(cat $IDS) 2>&1 | grep -E "^  QA |Error|ERROR|Traceback|WARNING" | tail -80
echo "== render done $(date +%T)"
