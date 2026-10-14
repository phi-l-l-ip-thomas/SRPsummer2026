#!/bin/bash

module load conda
conda activate base

source system.vars
cd ${MLCPPIPE}

# Declare scripts files as executables
chmod -R +x scripts
export PATH=scripts:${PATH}
chmod -R a+r inputs
chmod -R a+x slurm_jobs

# Create system directory skeleton
mkdir -p "simulations/${SYS_NAME}"
cd ${MLCPPIPE}/simulations/${SYS_NAME}

export CHECKPOINT_FILE="simulations/${SYS_NAME}/pipeline.checkpoint"

mkdir -p ${MLCPPIPE}/simulations/${SYS_NAME}/pbqff
mkdir -p ${MLCPPIPE}/simulations/${SYS_NAME}/nwchem
mkdir -p ${MLCPPIPE}/simulations/${SYS_NAME}/extension
mkdir -p ${MLCPPIPE}/simulations/${SYS_NAME}/mlcp

# -- process inputs
echo "Processing inputs..."
${MLCPPIPE}/scripts/input.py ${INPUT}
mv ${SYS_NAME}.toml pbqff/${SYS_NAME}.toml
mv intder.in pbqff
mv ${SYS_NAME}.mop pbqff
mv ${SYS_NAME}.nw nwchem
mv mlcp_${SYS_NAME}.inp mlcp

chmod -R a+r .