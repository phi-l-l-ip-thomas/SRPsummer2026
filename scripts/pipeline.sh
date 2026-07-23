#!/bin/bash

# pipeline.sh <input_file_path> <system_name>
if (( $# != 2 )); then
    echo 'Usage: $pipeline.sh <input_file> <system_name>' >&2
    exit 1
fi

echo 'Running MLCP pipeline...'

# Declare scripts files as executables
chmod -R +x /workspace/scripts
export PATH=/workspace/scripts:${PATH}
chmod -R a+r /workspace/inputs

# Run testing suite
echo "Running test suite..."
INPUT=$(realpath "$1")
SYS_NAME=$2

mkdir /workspace/simulations
cd /workspace/simulations
mkdir $SYS_NAME
cd $SYS_NAME
mkdir pbqff
mkdir nwchem
mkdir mlcp

# -- process inputs
echo "Processing inputs..."
input.py ${INPUT}
mv ${SYS_NAME}.toml pbqff/${SYS_NAME}.toml
mv intder.in pbqff
mv ${SYS_NAME}.nw nwchem
mv mlcp_${SYS_NAME}.inp mlcp

# -- run PBQFF
echo "Running PBQFF..."
cd pbqff
pbqff ${SYS_NAME}.toml
qfflist2.py pbqff.out ${SYS_NAME}
rm job.*
rm main*