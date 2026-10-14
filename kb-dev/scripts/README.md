########################################################################
#
# MLCP Pipe Scripts                                                    #
## Kaiwan Bilal, Phillip Thomas, Alexis Rana                          ##
#
########################################################################

### The Scripts

This directory houses the core of MLCP Pipe's automation.

Through a series of main shell scripts and python helper scripts, it works as follows:\
*enumeration matches designation in `checkpoint.sh`*

0) `../slurm_jobs/control.slurm` calls `checkpoint.sh` \
This is our main control file that submits each Slurm job and tracks completed steps

1) `setup.sh` is called, creating the working system directory and all input files

2) `../slurm_jobs/pbqff.slurm` is submitted, calling `pbqff.sh` within the container\
PBQFF is run alongside its post-processing script, `pbqff_fc.py`

3) `../slurm_jobs/nwchem.slurm` is submitted, calling `nwchem.sh` within the container\
NWChem is run alongside its post-processing script, `nwchem_fc.py`\
`translation.py` is also run to align normal mode bases

4) `../slurm_jobs/mlcp.slurm` is submitted, calling `mlcp.sh` within the container