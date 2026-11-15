#!/bin/bash
# rerender_gate.sh MAX: keeps at most MAX renders (mannequin.py render) running; claims the next lote_R*.txt (mkdir lock),
# runs render_part then post_part. Also runs post_part for the lotes in $ORPH once their render is done.
S=${KINETI_OPS:-/mnt/e/mannequin/avatar_man/ops}; HERE="$(cd "$(dirname "$0")" && pwd)"; mkdir -p $S/claims
F=/mnt/e/mannequin/avatar_man/final; MAX=${1:-2}; ORPH="${ORPH:-}"  # lotes ja renderizados que so precisam do post_part
while true; do
  for o in $ORPH; do
    if grep -q "== render done" $S/lote_$o.log 2>/dev/null && [ ! -e $S/claims/$o.post ]; then
      touch $S/claims/$o.post; echo "rerender $o rendered $(date +%T)" >> $S/rerender_run.log
      ( $HERE/post_part.sh $o >> $S/lote_$o.log 2>&1; echo "rerender $o done $(date +%T)" >> $S/rerender_run.log ) &
    fi
  done
  running=$(pgrep -fc "mannequin.py render")
  if [ "$running" -lt "$MAX" ]; then
    got=
    for f in $(ls $F/lotes/lote_R*.txt | sort); do n=$(basename $f .txt); n=${n#lote_}; mkdir $S/claims/$n 2>/dev/null && { got=$n; break; }; done
    if [ -n "$got" ]; then
      ( $HERE/render_part.sh $got > $S/lote_$got.log 2>&1; echo "rerender $got rendered $(date +%T)" >> $S/rerender_run.log
        $HERE/post_part.sh $got >> $S/lote_$got.log 2>&1; echo "rerender $got done $(date +%T)" >> $S/rerender_run.log ) &
      sleep 60; continue
    fi
    # nothing left to claim: finish when no render and all orphans posted
    if [ "$running" -eq 0 ]; then break; fi
  fi
  sleep 30
done
wait
echo "rerender all done $(date +%T)" >> $S/rerender_run.log
