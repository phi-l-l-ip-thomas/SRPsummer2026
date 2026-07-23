#!/bin/bash
set -e

# Activate conda base environment and run pipeline.sh
conda run -n base /workspace/scripts/pipeline_test.sh /workspace/inputs/sample.inp h2oT
