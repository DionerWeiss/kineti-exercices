"""Caminhos comuns dos scripts Python de ops. Mesmos padrões e variáveis KINETI_* de env.sh."""
import os
from pathlib import Path
R = os.environ.get('KINETI_REPO', str(Path(__file__).resolve().parents[3]))
M = R + '/tool/mannequin'
F = os.environ.get('KINETI_FINAL', '/mnt/e/mannequin/avatar_man/final')
O = os.environ.get('KINETI_OUT', '/mnt/e/mannequin/avatar_man/out')
FIX = os.environ.get('KINETI_FIX', '/mnt/e/mannequin/avatar_man/fix')
VID = os.environ.get('KINETI_VIDEOS', O + '/videos_final')
S = os.environ.get('KINETI_OPS', '/mnt/e/mannequin/avatar_man/ops')
