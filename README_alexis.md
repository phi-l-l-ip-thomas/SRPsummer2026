# Multifidelity PES Pipeline — Alexis Rana (SRP 2026)

## Key Results
- Multifidelity convergence (water, ±0.30 Bohr, NWChem/STO-3G):
  - Mode 1 (bend):    10 cm-1 with 21 NWChem pts (MOPAC: 558 cm-1, 56x improvement)
  - Mode 2 (O-H asym): 42 cm-1 with 21 NWChem pts (MOPAC: 2175 cm-1, 52x improvement)
  - Mode 3 (O-H sym):  32 cm-1 with 21 NWChem pts (MOPAC: 2356 cm-1, 74x improvement)
- MLCP read-morse-tanh validated vs HCl: exact match 2849.74 cm-1
- Methanol: 12 modes + 66 2D pairs + 4 3D triples fitted

## Coordinate Convention (read-morse-tanh)
- Morse_*.dat stores FULL omega (MLCP divides by 2 internally since commit fa83660)
- alpha/beta in dimensionless HO units: alpha_mlcp = alpha_bohr / sqrt(mu*omega/hbar)
- dividefc='F' for directly-fitted coefficients
- Path length: pes_path + '/fNwater.dat' must be < 128 chars (MLCP char(128) limit)

## Known Issues
- Coupled node (3-mode) overflows due to large coupling coefficients for modes involving
  O-H asym stretch (mode 2). MOPAC GPR for mode 2 is unphysical beyond q=1.28 Bohr,
  causing large 2D coupling surface values (~4000 cm-1). Fix requires MP2/DFT data.
- 3D coupling overflow: max_coeff ~7872 cm-1, too large for MLCP basis.

## Directory Structure
- water_pipeline/   : GPR fitting scripts + MLCP input files + Morse_water.dat
- methanol_pipeline/: Morse_methanol.dat (12 modes, full omega convention)
- hcl_validation/   : HCl read-morse-tanh validation (exact match confirmed)
