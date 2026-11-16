#!/bin/bash
# full_build.sh: every kineti + forked desk-break move -> kineti_sub -> the lib ($KINETI_LIB, default the final lib)
source "$(dirname "$0")/env.sh"
cd $R
export MANNEQUIN_AVATAR=$LIB MANNEQUIN_OUT=$F MANNEQUIN_RES=1920x1080
M="$(python3 -c "
import json
for f in ('kineti_moves.json','deskbreak_moves.json'):
    print(' '.join(e['id'] for e in json.load(open('tool/mannequin/'+f,encoding='utf-8'))['exercises']))
")"
echo "$M" | wc -w
date; python3 tool/mannequin/mannequin.py build $M 2>&1 | grep -E "Error|ERROR|Traceback|WARNING|OK" | tail -40
date; python3 tool/mannequin/mannequin.py sync $M 2>&1 | tail -3
date
