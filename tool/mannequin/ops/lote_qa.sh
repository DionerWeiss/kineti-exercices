#!/bin/bash
# lote_qa.sh NN: QA (layers 1+2, no render) of lote NN on a scratch lib (KINETI_QA_LIB); lists the jobs with a quebrado issue
source "$(dirname "$0")/env.sh"
cd $R
export MANNEQUIN_AVATAR="${KINETI_QA_LIB:-/mnt/e/mannequin/avatar_man/exercises_scratch.blend}" MANNEQUIN_OUT=$F MANNEQUIN_RES=1920x1080
python3 tool/mannequin/mannequin.py qa $(cat $F/lotes/lote_$1.txt) > /dev/null 2>&1
cd $F; python3 -c "
import json
from collections import Counter
c=Counter()
for i in open('lotes/lote_$1.txt').read().split():
    try: q=json.load(open(f'qa/{i}.json')); m=json.load(open(f'qa/{i}.motion.json'))
    except FileNotFoundError: print(i,'-'); continue
    c[(q['status'][:4],m['motion_status'][:4])]+=1
    a=[x['msg'][:58] for x in q['issues'] if x['sev']>=2]; b=[x['msg'][:58] for x in m['motion_issues'] if x['sev']>=2]
    if a or b: print(i,'|','; '.join(a+b))
print(dict(c))"
