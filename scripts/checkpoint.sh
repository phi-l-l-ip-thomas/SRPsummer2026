#!/bin/bash
set -e

# Load user-defined system vars
cd /global/cfs/cdirs/m5128/kbilal/interface
VARS_FILE="inputs/system.vars"
source ${VARS_FILE}
mkdir -p simulations/${SYS_NAME}
CHECKPOINT_FILE="simulations/${SYS_NAME}/pipeline.checkpoint"
POLL_INTERVAL="10"


# Read last completed step (0 if none)
if [ -f "$CHECKPOINT_FILE" ]; then
    LAST_STEP=$(cat "$CHECKPOINT_FILE")
else
    LAST_STEP=0
fi

run_step() {
    STEP_NUM=$1
    STEP_NAME=$2
    shift 2

    if [ "$STEP_NUM" -le "$LAST_STEP" ]; then
        echo "Skipping step $STEP_NUM ($STEP_NAME) — already completed"
        return
    fi

    echo "Running step $STEP_NUM: $STEP_NAME"
    "$@"

    if [ $? -eq 0 ]; then
        echo "$STEP_NUM" > "$CHECKPOINT_FILE"
        echo "Step $STEP_NUM ($STEP_NAME) submitted, checkpoint saved"
    else
        echo "Step $STEP_NUM ($STEP_NAME) failed, stopping"
        exit 1
    fi
}

step2_submit_pbqff() {
    pbqff_jobid=$(sbatch --parsable slurm_jobs/pbqff.slurm)
    echo "" >> "$VARS_FILE"
    echo "PBQFF_JOBID=$pbqff_jobid" >> "$VARS_FILE"
    while squeue -j "$pbqff_jobid" | grep -q "$pbqff_jobid"; do
        sleep "$POLL_INTERVAL"
    done
}

step3_submit_nwchem() {
    nwchem_jobid=$(sbatch --parsable \
                    --dependency=afterok:$pbqff_jobid \
                    --kill-on-invalid-dep=yes \
                    slurm_jobs/nwchem.slurm)
    echo "NWCHEM_JOBID=$nwchem_jobid" >> "$VARS_FILE"
    while squeue -j "$nwchem_jobid" | grep -q "$nwchem_jobid"; do
        sleep "$POLL_INTERVAL"
    done
}

step4_submit_mlcp() {
    mlcp_jobid=$(sbatch --parsable \
                   --dependency=afterok:$nwchem_jobid \
                   --kill-on-invalid-dep=yes \
                   slurm_jobs/mlcp.slurm)
    echo "MLCP_JOBID=$mlcp_jobid" >> "$VARS_FILE"
    while squeue -j "$mlcp_jobid" | grep -q "$mlcp_jobid"; do
        sleep "$POLL_INTERVAL"
    done
}

source "$VARS_FILE"
run_step 1 "setup" scripts/setup.sh

run_step 2 "pbqff" step2_submit_pbqff
source "$VARS_FILE"

run_step 3 "nwchem" step3_submit_nwchem
source "$VARS_FILE"

run_step 4 "mlcp" step4_submit_mlcp
source "$VARS_FILE"

echo "Pipeline complete!"