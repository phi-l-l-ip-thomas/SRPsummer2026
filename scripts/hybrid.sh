#!/bin/bash

# pipeline.sh <input_file_path> <system_name>
if (( $# != 2 )); then
    echo 'Usage: $hybrid.sh <input_file> <system_name>' >&2
    exit 1
fi

module load conda
conda run -n base

# Declare scripts files as executables
chmod -R +x scripts
export PATH=scripts:${PATH}
chmod -R a+r inputs
chmod -R a+x slurm_jobs

# Define environment
echo "Defining env vars..."
INPUT=$(realpath "$1")
SYS_NAME=$2

mkdir simulations
cd simulations
mkdir $SYS_NAME
cd $SYS_NAME
mkdir pbqff
mkdir nwchem
mkdir mlcp

# Submit PBQFF to CPU
echo 'Running MLCP pipeline...'
pbqff_jobid=$(sbatch --parsable ../../slurm_jobs/pbqff.slurm)
echo "Submitted pbqff job: $pbqff_jobid"

# Submit rest to GPU (successful PBQFF)
nwchem_jobid=$(sbatch --parsable \
                   --dependency=afterok:$pbqff_jobid \
                   --kill-on-invalid-dep=yes \
                   --dependency=afterok:$pbqff_jobid \
                   --kill-on-invalid-dep=yes \
                   ../../slurm_jobs/nwchem.slurm)
echo "Submitted NWChem job: $nwchem_jobid (afterok:$pbqff_jobid)"

# Submit rest to GPU (successful PBQFF)
mlcp_jobid=$(sbatch --parsable \
                   --dependency=afterok:$nwchem_jobid \
                   --kill-on-invalid-dep=yes \
                   --dependency=afterok:$nwchem_jobid \
                   --kill-on-invalid-dep=yes \
                   ../../slurm_jobs/mlcp.slurm)
echo "Submitted MLCP job: $mlcp_jobid (afterok:$nwchem_jobid)"