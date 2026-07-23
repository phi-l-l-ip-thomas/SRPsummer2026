#!/bin/bash
set -e

# Activate conda base environment and run pipeline.sh
# conda run -n base /workspace/scripts/pipeline_test.sh /workspace/inputs/sample.inp h2o
conda run -n base /workspace/scripts/pipeline.sh /workspace/inputs/napthalene.inp napthalene
# /workspace/scripts/pipeline.sh /workspace/inputs/anthracene.inp anthracene
# /workspace/scripts/pipeline.sh /workspace/inputs/sample.inp h2o3
