#!/bin/bash

set -euo pipefail
pwd
source /workspace/inputs/system.vars
cd /workspace/simulations/${SYS_NAME}/pbqff

conda activate base

# -- run PBQFF
echo "Running PBQFF..."
pbqff ${SYS_NAME}.toml
/workspace/scripts/qfflist2.py pbqff.out ${SYS_NAME}
rm job.*
rm main*

echo "CPU step complete."