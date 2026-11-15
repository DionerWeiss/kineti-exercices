"""pts.py <id> <points comma> [step]: tracked joint positions (x y z, m) through the motion + selected angles."""
import sys, numpy as np, json
D = np.load(f'/mnt/e/mannequin/avatar_man/final/qa/{sys.argv[1]}.motion.npz'); tr = list(D['track']); P = D['pts']
names = sys.argv[2].split(','); st = int(sys.argv[3]) if len(sys.argv) > 3 else 10
for f in range(0, len(P), st):
    print(f'{f:4d} ' + ' | '.join(f"{n} {np.round(P[f, tr.index(n)], 2).tolist()}" for n in names))
