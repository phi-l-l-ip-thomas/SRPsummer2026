#!/bin/bash

set -euo pipefail
source /workspace/inputs/system.vars
cd /workspace/simulations/${SYS_NAME}/mlcp

conda activate base

# -- process intermediaries and run MLCP
echo "Processing intermediaries and running MLCP..."
cp /workspace/outputs/pbqff2_nmodes_h2o.dat ../pbqff # temporary, until isolated from pbqff
/workspace/scripts/translation.py ${SYS_NAME}
mkdir pes
mv ../nwchem/nwcf2${SYS_NAME}.dat ./pes/f2${SYS_NAME}.dat
mv ../pbqff/f3${SYS_NAME}.dat ./pes
mv ../pbqff/f4${SYS_NAME}.dat ./pes
mlcp.x mlcp_${SYS_NAME}.inp > mlcp_${SYS_NAME}.out

echo "GPU step complete."
echo 'Completed MLCP pipeline!'