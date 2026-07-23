#!/bin/bash

# Activate conda base environment and run pipeline.sh
echo "Running interactive test..."
conda run -n base /workspace/scripts/pipeline_test.sh /workspace/inputs/sample.inp h2o

# Start interactive shell in conda environment
conda run -n base /bin/bash -i
