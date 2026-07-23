#!/bin/bash

set -euo pipefail
source /path/to/conda/etc/profile.d/conda.sh
conda activate base

# -- run NWChem
echo "Running NWChem..."
cd ../nwchem
nwchem ${SYS_NAME}.nw > nwc_${SYS_NAME}.out
nwchem_fc.py nwc_${SYS_NAME}.out ${SYS_NAME}

# -- process intermediaries and run MLCP
echo "Processing intermediaries and running MLCP..."
cd ../mlcp
cp /workspace/outputs/pbqff2_nmodes_h2o.dat ../pbqff # temporary, until isolated from pbqff
translation.py ${SYS_NAME}
mkdir pes
mv ../nwchem/nwcf2${SYS_NAME}.dat ./pes/f2${SYS_NAME}.dat
mv ../pbqff/f3${SYS_NAME}.dat ./pes
mv ../pbqff/f4${SYS_NAME}.dat ./pes
mlcp.x mlcp_${SYS_NAME}.inp > mlcp_${SYS_NAME}.out

echo "GPU step complete."
echo 'Completed MLCP pipeline!'