#!/bin/bash

#SBATCH --job-name=pbqff
#SBATCH --account=m5128           
#SBATCH --constraint=cpu
#SBATCH --qos=debug        
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=00:10:00
#SBATCH --output=cpu_job_%j.out
#SBATCH --error=cpu_job_%j.err

# OpenMP settings:
export OMP_NUM_THREADS=1
export OMP_PLACES=threads
export OMP_PROC_BIND=spread

#run the application: 
# applications may perform better with --gpu-bind=none instead of --gpu-bind=single:1
srun -n 1 -c 128 --cpu_bind=cores podman-hpc run --userns=keep-id --rm -v "/global/cfs/cdirs/m5128/kbilal/interface":/workspace --entrypoint="/workspace/scripts/pbqff.sh" working