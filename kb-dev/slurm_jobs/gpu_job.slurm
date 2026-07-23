#!/bin/bash
#SBATCH --job-name=gpu_job
#SBATCH --account=m5128
#SBATCH --constraint=gpu         
#SBATCH --qos=regular
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1      
#SBATCH --cpus-per-task=32
#SBATCH --time=02:00:00
#SBATCH --output=gpu_job_%j.out
#SBATCH --error=gpu_job_%j.err


# OpenMP settings:
export OMP_NUM_THREADS=1
export OMP_PLACES=threads
export OMP_PROC_BIND=spread

#run the application: 
# applications may perform better with --gpu-bind=none instead of --gpu-bind=single:1
srun -n 1 -c 128 --cpu_bind=cores -G 1 --gpu-bind=single:1 podman-hpc run --userns=keep-id --rm --gpu -v "$PWD":/workspace --entrypoint="/workspace/scripts/gpu.sh" working