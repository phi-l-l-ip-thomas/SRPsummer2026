#!/bin/bash

set -euo pipefail
source /workspace/inputs/system.vars
cd /workspace/simulations/${SYS_NAME}/nwchem

conda activate base

# -- run NWChem
echo "Running NWChem..."
nwchem ${SYS_NAME}.nw > nwc_${SYS_NAME}.out
/workspace/scripts/nwchem_fc.py nwc_${SYS_NAME}.out ${SYS_NAME}