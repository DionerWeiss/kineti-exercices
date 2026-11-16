#!/bin/bash
# post_part.sh NN: PP compare + contact sheet + per-lote review csv of lote NN
source "$(dirname "$0")/env.sh"
N=$1; IDS=$F/lotes/lote_$N.txt
cd $R
export MANNEQUIN_OUT=$F MANNEQUIN_VIDEOS=$VID PP_COMPARE=$O/compare
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py fetch $(cat $IDS) 2>&1 | tail -3
uv run -q --no-project --with numpy python3 tool/mannequin/pp_compare.py compare $(cat $IDS) 2>&1 | grep -E "Error|Traceback" | tail -5
echo "== compare done $(date +%T)"
cd tool/mannequin
python3 contact_sheet.py $VID $IDS $O/contact_lote_$N.png $F/qa 2>&1 | tail -1
python3 review.py $F $VID $IDS review_lote_$N.csv 2>&1 | tail -6
echo "== lote $N end $(date +%T)"
