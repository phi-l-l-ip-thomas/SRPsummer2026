# Multifidelity PES Pipeline — Alexis Rana (SRP 2026)

## Project
Automated vibrational PES fitting pipeline for water (3 modes) and methanol (12 modes).
Uses multifidelity Gaussian Process Regression (GPR) combining cheap MOPAC semiempirical 
data with a few expensive ab initio points to achieve spectroscopic accuracy.

## Key Results
- Multifidelity convergence (water, ±0.30 Bohr, STO-3G correction):
  - Mode 1 (bend):    10 cm-1 with 21 NWChem pts (MOPAC baseline: 558 cm-1)
  - Mode 2 (O-H asym): 42 cm-1 with 21 NWChem pts (MOPAC baseline: 2175 cm-1)
  - Mode 3 (O-H sym):  32 cm-1 with 21 NWChem pts (MOPAC baseline: 2356 cm-1)
- MLCP read-morse-tanh validated against HCl: exact match (2849.74 cm-1)
- Methanol: all 12 modes + 66 2D coupling pairs + 4 3D triples fitted

## Coordinate Convention (read-morse-tanh)
- Morse_*.dat stores omega/2 (not omega) as the KEO prefactor
- alpha/beta stored in dimensionless HO units: alpha_mlcp = alpha_bohr / sqrt(mu*omega/hbar)
- dividefc='F' for directly-fitted coefficients
- Coupling coefficients: as fitted (no alpha^power division needed)

## Directory Structure
- water_pipeline/   : GPR fitting scripts + water MLCP input files
- methanol_pipeline/: Morse_methanol.dat with all 12 modes
- hcl_validation/   : HCl read-morse-tanh validation files

## Dependencies
Python: numpy, sklearn, joblib, scipy, matplotlib
MLCP: MorsifyDirect branch (https://github.com/phi-l-l-ip-thomas/mlcp)
