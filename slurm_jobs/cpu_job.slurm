#!/bin/bash
#SBATCH --job-name=cpu_job
#SBATCH --account=m5128           
#SBATCH --constraint=cpu
#SBATCH --qos=debug        
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=128      
#SBATCH --time=00:30:00
#SBATCH --output=cpu_job_%j.out
#SBATCH --error=cpu_job_%j.err

# OpenMP settings:
export OMP_NUM_THREADS=1
export OMP_PLACES=threads
export OMP_PROC_BIND=spread

#run the application: 
# applications may perform better with --gpu-bind=none instead of --gpu-bind=single:1
srun -n 1 -c 128 --cpu_bind=cores podman-hpc run --userns=keep-id --rm --gpu -v "$PWD":/workspace --entrypoint="/workspace/scripts/cpu.sh" working