########################################################################
#
# Pipeline Automation for MLCP                                        #
## Kaiwan Bilal, Phillip Thomas, Alexis Rana                         ##
#
########################################################################

### The Pipeline

Multi-Layer Cannonical Polyadic, or MLCP, molecular modeling (as created by Phillip Thomas 
at Lawrence-Berkeley National Lab) enables computational researchers to employ a fully variational 
method of modeling molecular vibrational spectra without requiring an obscene amount of computer resources.

On its own, MLCP simulates such molecular vibrational spectra using a series of user-provided harmonic, 
cubic, and quartic force constants for a Potential Energy Surface (PES) describing the system of interest. 
Generating a viable PES usually calls another pre-existing electronic structure package and generally
only yields harmonic force constants, but MLCP is built to consider fourth-order anharmonicity. 

**That's where this pipeline comes in!**

Our pipeline automates this collective process from start to finish. Calling Push-Button Quartic Force Fields,
MOPAC, NWChem, and MLCP, users provide a "master" input file (as shown in `inputs/sample.inp`), which is a combined
input document merging PBQFF, NWChem, and MLCP into one joint input file for the pipeline.

### Installation

The entire pipeline is contained within a multi-stage Podman/Docker Container for ease of distribution.

1) Download the container and cd into the root directory `interface`

2) Build the container set (replace `podman-hpc` with respective container handler)

```bash
podman-hpc build -f ./containers/Containerfile_env -t env .
podman-hpc build -f ./containers/Containerfile_working -t working .

podman-hpc migrate working # If needed, for HPC centers
```

### Usage

This entire `interface` directory gets mounted into the container, so users can 
simply add/create/modify files within the interface directory for pipeline use.

1) Create a plain-text input file following this model (complete version in `inputs/sample.inp`)

```bash
# System Name
system_name = h2o

# Geometry
 O       0.0  0.0  1.0  
...
--

# PBQFF Input
charge = 0
optimize = true
...
-- 
# Intder.in
# INTDER ##########################
    3    3    3    0    0    3    0    0    0    1    0    0    0    1    1    0
STRE     1    2
...
--

# NWChem Input
BASIS  
 H library sto-3g  
 O library sto-3g  
...
--

# MLCP Input
$control
system='h2o'
rs='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0'
...
--
```

If you've worked with any of these models, you'll notice that each section (with the exception 
of a shared geometry input) is simply a complete input file for running standalone calculations 
with package. Each section is copied directly into individual input files, allowing users to 
fully tune all available parameters granted by each standalone component.

2) Edit your job files

The pipeline can be called by

```bash
/workspace/scripts/pipeline.sh <input file path> <system name of choice>

# example
/workspace/scripts/pipeline.sh /workspace/inputs/sample.inp h2o
```

updating the names as needed when you call the pipeline.

If you're running these calculations locally, the commands above are minimally sufficient.
If you're planning on submitting jobs through Slurm, edit the entrypoint bash script(s)
`scripts/entrypoint*.sh` as desired.

`scripts/entrypoint_it.sh` automatically runs a quick example simulation with water and
opens an interactive bash terminal for calling the pipeline.

`scripts/entrypoint_batch.sh` is designed for submitting your system as a batch job.
It also automatically runs the test simulation, but should be modified to include jobs of choice:

```bash
conda run -n base /workspace/scripts/pipeline_test.sh /workspace/inputs/sample.inp h2o
/workspace/scripts/pipeline.sh <choice input> <choice system>
```

Queueing independent jobs in series is also supported

```bash
conda run -n base /workspace/scripts/pipeline_test.sh /workspace/inputs/sample.inp h2o
/workspace/scripts/pipeline.sh <input 1> <system 1>
/workspace/scripts/pipeline.sh <input 2> <system 2>
/workspace/scripts/pipeline.sh <input 3> <system 3>
/workspace/scripts/pipeline.sh <input 4> <system 4>
```

3) Run the container

- Running local interactive session

```bash
podman-hpc run --rm -it --gpu -v "$PWD":/workspace --entrypoint="/workspace/scripts/entrypoint_it.sh" working
```

- Slurm job (batch)

```bash
sbatch slurm_jobs/mlcp_it.slurm
```