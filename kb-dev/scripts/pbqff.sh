#!/bin/bash

set -euo pipefail
source /workspace/system.vars
cd /workspace/simulations/${SYS_NAME}/pbqff

# -- run PBQFF
echo "Running PBQFF..."

if [ -f ".tmp*" ]; then
    pbqff -c ${SYS_NAME}.toml
elif [[ ! -f f*{SYS_NAME}.dat ]]; then
    pbqff -o ${SYS_NAME}.toml
fi

mopac ${SYS_NAME}.mop
mv ${SYS_NAME}.out mopac.out
conda run -n base /workspace/scripts/pbqff_fc.py pbqff.out ${SYS_NAME}

echo "CPU step complete."