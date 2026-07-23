#!/bin/bash

module load conda
conda activate base

cd /global/cfs/cdirs/m5128/kbilal/interface

# Declare scripts files as executables
chmod -R +x scripts
export PATH=scripts:${PATH}
chmod -R a+r inputs
chmod -R a+x slurm_jobs

# Create system directory skeleton
cd /global/cfs/cdirs/m5128/kbilal/interface/simulations/${SYS_NAME}

mkdir -p /global/cfs/cdirs/m5128/kbilal/interface/simulations/${SYS_NAME}/pbqff
mkdir -p /global/cfs/cdirs/m5128/kbilal/interface/simulations/${SYS_NAME}/nwchem
mkdir -p /global/cfs/cdirs/m5128/kbilal/interface/simulations/${SYS_NAME}/mlcp

# -- process inputs
echo "Processing inputs..."
/global/cfs/cdirs/m5128/kbilal/interface/scripts/input.py ${INPUT}
mv ${SYS_NAME}.toml pbqff/${SYS_NAME}.toml
mv intder.in pbqff
mv ${SYS_NAME}.nw nwchem
mv mlcp_${SYS_NAME}.inp mlcp