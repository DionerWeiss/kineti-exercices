#!/bin/bash
# full_build.sh: every kineti + forked desk-break move -> kineti_sub -> the final lib
cd /home/dioner/projects/kineti/animated_exercices
export MANNEQUIN_AVATAR=/mnt/e/mannequin/avatar_man/exercises_final.blend MANNEQUIN_OUT=/mnt/e/mannequin/avatar_man/final MANNEQUIN_RES=1920x1080
M="$(python3 -c "
import json
for f in ('kineti_moves.json','deskbreak_moves.json'):
    print(' '.join(e['id'] for e in json.load(open('tool/mannequin/'+f,encoding='utf-8'))['exercises']))
")"
echo "$M" | wc -w
date; python3 tool/mannequin/mannequin.py build $M 2>&1 | grep -E "Error|ERROR|Traceback|WARNING|OK" | tail -40
date; python3 tool/mannequin/mannequin.py sync $M 2>&1 | tail -3
date
