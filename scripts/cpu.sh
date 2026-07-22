#!/bin/bash

set -euo pipefail
source /path/to/conda/etc/profile.d/conda.sh
conda activate base

# -- process inputs
echo "Processing inputs..."
input.py ${INPUT}
mv ${SYS_NAME}.toml pbqff/${SYS_NAME}.toml
mv intder.in pbqff
mv ${SYS_NAME}.nw nwchem
mv mlcp_${SYS_NAME}.inp mlcp

# -- run PBQFF
echo "Running PBQFF..."
cd pbqff
pbqff ${SYS_NAME}.toml
qfflist2.py pbqff.out ${SYS_NAME}
rm job.*
rm main*

echo "CPU step complete."