#!/bin/bash
# gen.sh <joints.json> <out dir> <list file: "<action> [drive_puppet flags]" per line>
# -> <out>/<action>.json (Lottie, one cycle) + .mp4 (1080 px, 60 fps, >= 2 cycles, >= 10 s) + strips/ + qa/
HERE="$(cd "$(dirname "$0")" && pwd)"
J=$1; O=$2; LIST=$3
SRC=${PUPPET_SRC:-/mnt/e/mannequin/puppet2d/scripts/split-jump-dinh.json}
mkdir -p "$O/strips" "$O/qa"
while read -r id flags; do
  [ -z "$id" ] && continue
  uv run -q --no-project --with numpy python3 -I "$HERE/drive_puppet.py" "$SRC" "$J" "$id" "$O/$id.json" --kineti $flags \
    > "$O/qa/$id.log" 2>&1 < /dev/null || { echo "FAIL $id"; tail -3 "$O/qa/$id.log"; continue; }
  node "$HERE/render.mjs" "$O/$id.json" "$O/$id.mp4" 1080 2 10 > /dev/null 2> "$O/qa/$id.render.err" < /dev/null || { echo "RENDERFAIL $id"; continue; }
  ffmpeg -nostdin -v error -y -i "$O/$id.mp4" -vf "fps=1.2,scale=270:-1,tile=8x1" -frames:v 1 "$O/strips/$id.png"
  echo "ok $id $(grep '^QA' "$O/qa/$id.log" | cut -c4-200)"
done < "$LIST"
