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

## Day 17 Updates (July 21, 2026)
- GPR centering fix: shift q so MOPAC minimum -> q=0; mode 1 SOP RMSE 435->45 cm-1
- Residual coupling: V_2D - V_1D_i - V_1D_j on uniform +-0.40 Bohr grid
  - Pair (1,2): RMSE=2.23, max_coeff=28 cm-1
  - Pair (1,3): RMSE=0.15, max_coeff=1.2 cm-1 (nearly zero)
  - Pair (2,3): RMSE=2.93, max_coeff=29 cm-1
- All pairwise 2-mode MLCP runs validated, no overflow
- 3-mode overflow remains (mode 2 De~70k cm-1 expected per Dr Thomas)

## FINAL RESULT (July 21, 2026)
Full 3-mode water pipeline working end-to-end:
- GPR centering fix (q_shift per mode)
- Residual coupling: V_2D - V_1D_i - V_1D_j on uniform +-0.40 Bohr grid
- MLCP with truncation layer (9->5 per mode, 40 combined)
- Result: ZPVE=3827, FUND v1=1440, FUND v2=3561, FUND v3=2710 cm-1
- No overflow, all levels physical, delta~1e-9
