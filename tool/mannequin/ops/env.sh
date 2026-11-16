# env.sh: caminhos comuns dos scripts de ops (source "$(dirname "$0")/env.sh").
# Os padrões são os da entrega atual. Para trabalhar numa versão separada, defina as variáveis KINETI_*
# (docs/pipeline/agentes/avaliar_e_corrigir.md). O repo é o que contém este script (uma worktree aponta para si mesma).
R="${KINETI_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
F="${KINETI_FINAL:-/mnt/e/mannequin/avatar_man/final}"
O="${KINETI_OUT:-/mnt/e/mannequin/avatar_man/out}"
LIB="${KINETI_LIB:-/mnt/e/mannequin/avatar_man/exercises_final.blend}"
VID="${KINETI_VIDEOS:-$O/videos_final}"
S="${KINETI_OPS:-/mnt/e/mannequin/avatar_man/ops}"
