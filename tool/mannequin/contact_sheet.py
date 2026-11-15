"""Contact sheet of finished videos: tool/mannequin/contact_sheet.py <videos dir> <ids file> <out.png> [<qa dir> [cols]]
One row per video: `cols` frames spread over the clip (default 6), labelled with the id and, when the qa dir is
given, the automatic status. Rows are 1920/cols wide (320 px for 6)."""
import json, subprocess, sys, tempfile
from pathlib import Path

vids, ids, out = Path(sys.argv[1]), open(sys.argv[2]).read().split(), Path(sys.argv[3])
qa = Path(sys.argv[4]) if len(sys.argv) > 4 else None
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 6
W = 1920 // cols
H = W * 9 // 16
tmp = Path(tempfile.mkdtemp())
rows = []
for k, i in enumerate(ids):
    v = vids / f'{i}.mp4'
    if not v.exists():
        continue
    n = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v:0', '-show_entries',
                            'stream=nb_read_packets', '-of', 'csv=p=0', str(v)], capture_output=True, text=True).stdout.strip())
    picks = [round(c * (n - 1) / cols) for c in range(cols)]
    st = ''
    if qa and (qa / f'{i}.json').exists():
        st = json.load(open(qa / f'{i}.json', encoding='utf-8'))['status']
    color = {'ok': '0x15803D', 'suspeito': '0xB45309', 'quebrado': '0xB91C1C'}.get(st, '0x334155')
    label = f'{i}  {st}'.replace(':', '\\:')
    sel = '+'.join(f'eq(n\\,{p})' for p in picks)
    row = tmp / f'r{k:04d}.png'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-nostdin', '-i', str(v), '-vf',
                    f"select='{sel}',scale={W}:{H},tile={cols}x1,drawtext=text='{label}':x=8:y=6:fontsize=20:fontcolor={color}:box=1:boxcolor=white@0.7",
                    '-frames:v', '1', '-vsync', '0', str(row)], check=True)
    rows.append(row)
inputs = sum((['-i', str(r)] for r in rows), [])
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-nostdin', *inputs, '-filter_complex',
                ''.join(f'[{k}]' for k in range(len(rows))) + f'vstack=inputs={len(rows)}', str(out)] if len(rows) > 1 else
               ['cp', str(rows[0]), str(out)], check=True)
print(out, len(rows), 'videos')
