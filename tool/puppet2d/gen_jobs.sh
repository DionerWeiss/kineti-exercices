#!/bin/bash
# gen_jobs.sh <joints.json> <out dir> <list file: "<job> <action> <front|side|top|sidetop> [driver flags]" per line>
# One Lottie per jobs.json job (jobs sharing a move can differ in props/view), named by the job id:
# -> <out>/<job>.json (Lottie, one cycle) + <job>.mp4 (1080 px, 60 fps, >= 2 cycles, >= 10 s) + strips/<job>.png
#    + qa/<job>.log (driver output, QA line) + qa/<job>.json (the QA numbers, view, flags, timing)
# side -> drive_puppet.py on the Dinh split-jump man; front -> drive_front.py on front_puppet.json;
# top -> a supine/prone move seen from above: top_view.py rotates its joints upright, drive_front.py draws it laid down;
# sidetop -> a side-lying move seen from above: top_view.py --side, drawn in profile by drive_puppet.py, laid down.
HERE="$(cd "$(dirname "$0")" && pwd)"
J=$1; O=$2; LIST=$3
SRC_SIDE=${PUPPET_SRC:-/mnt/e/mannequin/puppet2d/scripts/split-jump-dinh.json}
SRC_FRONT=${PUPPET_FRONT:-$HERE/front_puppet.json}
mkdir -p "$O/strips" "$O/qa"
while read -r job act view flags; do
  [ -z "$job" ] && continue
  case "$job" in \#*) continue ;; esac
  t0=$(date +%s.%N)
  jj=$J
  case "$view" in side|sidetop) drv="$HERE/drive_puppet.py"; src=$SRC_SIDE ;; *) drv="$HERE/drive_front.py"; src=$SRC_FRONT ;; esac
  if [ "$view" = top ] || [ "$view" = sidetop ]; then
    jj="$O/qa/.top_$job.json"
    uv run -q --no-project --with numpy python3 -I "$HERE/top_view.py" "$J" "$act" "$jj" $([ "$view" = sidetop ] && echo --side) \
      > /dev/null < /dev/null || { echo "FAIL $job (top_view)"; continue; }
  fi
  uv run -q --no-project --with numpy python3 -I "$drv" "$src" "$jj" "$act" "$O/$job.json" --kineti $flags \
    > "$O/qa/$job.log" 2>&1 < /dev/null || { echo "FAIL $job"; tail -3 "$O/qa/$job.log"; [ "$jj" != "$J" ] && rm -f "$jj"; continue; }
  [ "$jj" != "$J" ] && rm -f "$jj"
  python3 -I "$HERE/lottie_despike.py" "$O/$job.json" >> "$O/qa/$job.log" 2>&1 < /dev/null    # one-frame twitches
  t1=$(date +%s.%N)
  node "$HERE/render.mjs" "$O/$job.json" "$O/$job.mp4" 1080 2 10 > /dev/null 2> "$O/qa/$job.render.err" < /dev/null \
    || { echo "RENDERFAIL $job"; continue; }
  ffmpeg -nostdin -v error -y -i "$O/$job.mp4" -vf "fps=1.2,scale=270:-1,tile=8x1" -frames:v 1 "$O/strips/$job.png"
  t2=$(date +%s.%N)
  qa=$(grep '^QA ' "$O/qa/$job.log" | head -1 | cut -c4-)
  python3 - "$O/qa/$job.json" "$job" "$act" "$view" "$flags" "${qa:-{\}}" "$t0" "$t1" "$t2" <<'EOF'
import json, sys
out, job, act, view, flags, qa, t0, t1, t2 = sys.argv[1:]
json.dump(dict(job=job, move=act, view=view, flags=flags.split(), qa=json.loads(qa),
               t_drive=round(float(t1) - float(t0), 1), t_render=round(float(t2) - float(t1), 1)), open(out, 'w'))
EOF
  echo "ok $job $view $qa"
done < "$LIST"
