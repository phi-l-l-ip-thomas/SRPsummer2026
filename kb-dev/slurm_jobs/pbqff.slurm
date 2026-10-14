#!/bin/bash

#SBATCH --job-name=pbqff
#SBATCH --constraint=cpu
#SBATCH --qos=debug       
#SBATCH --nodes=1
#SBATCH --time=00:30:00
#SBATCH --output=/global/cfs/cdirs/m5128/kbilal/interface/cpu_job_%j.out
#SBATCH --error=/global/cfs/cdirs/m5128/kbilal/interface/cpu_job_%j.err

# OpenMP settings:
export OMP_NUM_THREADS=1
export OMP_PLACES=threads
export OMP_PROC_BIND=spread
export RAYON_NUM_THREADS=128

#run the application: 
# applications may perform better with --gpu-bind=none instead of --gpu-bind=single:1
# srun -n 1 -c 256 --cpu_bind=cores 
source system.vars
cd ${MLCPPIPE}

podman-hpc run --userns=keep-id --rm -v "${MLCPPIPE}":/workspace --entrypoint="/workspace/scripts/pbqff.sh" working
