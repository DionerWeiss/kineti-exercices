"""blink.py <mp4>...: frames that differ from both neighbours much more than the neighbours differ from each other."""
import sys, subprocess, numpy as np
for f in sys.argv[1:]:
    w, h = 270, 152
    raw = subprocess.run(['ffmpeg','-v','error','-i',f,'-vf',f'scale={w}:{h},format=gray','-f','rawvideo','-'],capture_output=True).stdout
    V = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.int16)
    out = []
    for i in range(1, len(V)-1):
        a = np.abs(V[i]-V[i-1]) > 40; b = np.abs(V[i]-V[i+1]) > 40; c = np.abs(V[i+1]-V[i-1]) > 40
        s = (a & b).sum(); 
        if s > 25 and s > 3 * c.sum(): out.append((i, int(s), int(c.sum())))
    print(f.split('/')[-1], len(V), 'blinks', len(out), out[:8])
