#!/bin/bash
set -e

# Activate conda base environment and run pipeline.sh
conda run -n base /workspace/scripts/pipeline.sh /workspace/inputs/anthracene.inp anthraceneT
