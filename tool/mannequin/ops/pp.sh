#!/bin/bash
# usage: pp.sh <ppid...>  -> prints desc, makes tile in val/pp_<id>.png
source "$(dirname "$0")/env.sh"; mkdir -p $S/val
for P in "$@"; do
python3 -c "
import json,sys
pp=json.load(open('$R/research/pocketphysio/exercicios.json'))
for e in pp:
  if e['id']=='$P': print('$P', e['nome_pt'],'::', e['descricao_pt'][:700])
"
V=/mnt/e/mannequin/pocketphysio_ref/$P.mp4
[ -f $V ] || { echo NOPP $P; continue; }
N=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 $V)
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $V)
ST=$((N/8))
ffmpeg -v error -y -i $V -vf "select='not(mod(n\,$ST))',scale=480:-2,tile=4x2" -frames:v 1 $S/val/pp_$P.png
echo "  frames=$N dur=$D"
done
