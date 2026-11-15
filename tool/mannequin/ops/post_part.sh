#!/bin/bash
# post_part.sh NN: PP compare + contact sheet + per-lote review csv of lote NN
N=$1; F=/mnt/e/mannequin/avatar_man/final; O=/mnt/e/mannequin/avatar_man/out; IDS=$F/lotes/lote_$N.txt
cd /home/dioner/projects/kineti/animated_exercices
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py fetch $(cat $IDS) 2>&1 | tail -3
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py compare $(cat $IDS) 2>&1 | grep -E "Error|Traceback" | tail -5
echo "== compare done $(date +%T)"
cd tool/mannequin
python3 contact_sheet.py $O/videos_final $IDS $O/contact_lote_$N.png $F/qa 2>&1 | tail -1
python3 review.py $F $O/videos_final $IDS review_lote_$N.csv 2>&1 | tail -6
echo "== lote $N end $(date +%T)"
