#!/bin/bash
set -euo pipefail
source /workspace/system.vars

cd /workspace/simulations/${SYS_NAME}/nwchem
conda run -n base /workspace/scripts/nwchem_fc.py nwc_${SYS_NAME}.out ${SYS_NAME}

cd /workspace/simulations/${SYS_NAME}/mlcp
conda run -n base /workspace/scripts/translation.py ${SYS_NAME}
mv ../nwchem/nwcf2${SYS_NAME}.dat f2${SYS_NAME}.dat
mv ../pbqff/f3${SYS_NAME}.dat .
mv ../pbqff/f4${SYS_NAME}.dat .