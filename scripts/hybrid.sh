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
echo 'Running MLCP pipeline (CPU)...'
cpu_jobid=$(sbatch --parsable ../../slurm_jobs/cpu_job.slurm)
echo "Submitted pbqff (CPU) job: $cpu_jobid"

# Submit rest to GPU (successful PBQFF)
echo 'Running MLCP pipeline (GPU)...'
gpu_jobid=$(sbatch --parsable \
                   --dependency=afterok:$cpu_jobid \
                   --kill-on-invalid-dep=yes \
                   --dependency=afterok:$cpu_jobid \
                   --kill-on-invalid-dep=yes \
                   ../../slurm_jobs/gpu_job.slurm)
echo "Submitted GPU job: $gpu_jobid (afterok:$cpu_jobid)"