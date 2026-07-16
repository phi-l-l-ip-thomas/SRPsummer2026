"""
convert_2d_sop.py
------------------
Converts 2D coupling GPR residuals to tanh sum-of-products format
for MLCP, using the existing convert_2d_terms() infrastructure in
gpr_to_sop_mlcp.py.

Reads:
- 2D coupling GPR joblib models (2d_coupling_gpr_m*m*.joblib)
- Per-mode alphas from alphas_water.dat
- Per-mode 1D GPR joblib models for subtracting 1D contributions
- 2D MOPAC data from the coupling directories

Writes:
- f3water.dat (overwrites with 2D coupling terms added)
- Actually appends 2D terms to the existing f3/f4/etc files

Usage:
    python3 convert_2d_sop.py --molecule water --pairs 1,2 1,3 2,3
"""

import os, sys, re, csv, glob, argparse
import numpy as np
import joblib

# Add the working directory to path so we can import gpr_to_sop_mlcp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KCAL_TO_CM1 = 349.7551


def parse_hof(f):
    if not os.path.exists(f): return None
    txt = open(f).read()
    m = re.search(r'HEAT_OF_FORMATION:KCAL/MOL=([\d.\-+DE]+)', txt)
    return float(m.group(1).replace('D','E')) if m else None


def load_coupling_data(mode_i, mode_j, mopac_dir, job_index,
                       gpr_i, gpr_j, E_ref_kcal):
    """Load 2D MOPAC data and subtract 1D GPR predictions."""
    jobs = list(csv.DictReader(open(job_index)))
    Qi, Qj, R_2d = [], [], []
    for job in jobs:
        aux = os.path.join(mopac_dir,
              os.path.basename(job['input_file']).replace('.mop', '.aux'))
        hof = parse_hof(aux)
        if hof is None: continue
        E_2d = (hof - E_ref_kcal) * KCAL_TO_CM1
        qi = float(job['step_i_bohr'])
        qj = float(job['step_j_bohr'])
        V1 = gpr_i.predict([[qi]])[0]
        V2 = gpr_j.predict([[qj]])[0]
        Qi.append(qi); Qj.append(qj)
        R_2d.append(E_2d - V1 - V2)
    return np.array(Qi), np.array(Qj), np.array(R_2d)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--molecule", type=str, default="water")
    parser.add_argument("--pairs", type=str, nargs="+", default=["1,2","1,3","2,3"],
                        help="Mode pairs to convert e.g. '1,2 1,3 2,3'")
    parser.add_argument("--max-power", type=int, default=4,
                        help="Max power for each mode in 2D tanh basis")
    parser.add_argument("--alphas-file", type=str, default="alphas_water.dat")
    parser.add_argument("--outdir", type=str, default=".")
    args = parser.parse_args()

    # Import the conversion functions from gpr_to_sop_mlcp
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gpr_to_sop_mlcp", "gpr_to_sop_mlcp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Load alphas
    alpha_data = np.loadtxt(args.alphas_file)
    alphas = {int(row[0]): float(row[1]) for row in alpha_data}
    print(f"Loaded alphas: {alphas}")

    # Find equilibrium reference energy
    E_ref_kcal = min(parse_hof(f) for f in glob.glob('water_mode1_*.aux')
                     if parse_hof(f) is not None)

    # Load 1D GPR models
    gprs = {}
    for mode in [1, 2, 3]:
        mfile = f"sklearn_gpr_optimal_mode{mode}.joblib"
        if os.path.exists(mfile):
            gprs[mode] = joblib.load(mfile)

    print(f"\n=== 2D SOP conversion: {args.molecule} ===")

    # Config for each pair: (mode_i, mode_j, job_index, mopac_dir)
    pair_configs = {
        "1,2": ("2d_job_index_coupling12.csv", "2d_mopac_inputs_coupling"),
        "1,3": ("2d_job_index_coupling13.csv", "2d_mopac_inputs_coupling13"),
        "2,3": ("2d_job_index_coupling23.csv", "2d_mopac_inputs_coupling23"),
    }

    residual_2d_specs = []
    for pair_str in args.pairs:
        mi, mj = map(int, pair_str.split(","))
        if pair_str not in pair_configs:
            print(f"  Pair ({mi},{mj}): no config found, skipping")
            continue
        jidx, mdir = pair_configs[pair_str]
        if not os.path.exists(jidx):
            print(f"  Pair ({mi},{mj}): job index {jidx} not found, skipping")
            continue

        Qi, Qj, R_2d = load_coupling_data(
            mi, mj, mdir, jidx, gprs[mi], gprs[mj], E_ref_kcal)
        print(f"  Pair ({mi},{mj}): {len(Qi)} points, "
              f"residual RMS={np.sqrt(np.mean(R_2d**2)):.1f} cm-1")
        residual_2d_specs.append({
            "mode_i": mi, "mode_j": mj,
            "Qi": Qi, "Qj": Qj, "R_2d": R_2d
        })

    # Convert to SOP
    f3_lines = mod.convert_2d_terms(residual_2d_specs, alphas, args.max_power)

    # Write output files -- 2D coupling terms go into f3 (cubic) through
    # f<2*max_power> files, following MLCP's format
    # For a term tanh(alpha_i*qi)^p * tanh(alpha_j*qj)^q, order = p+q
    by_order = {}
    for mi, p, mj, q, c in f3_lines:
        order = p + q
        by_order.setdefault(order, []).append((mi, p, mj, q, c))

    print(f"\n  Writing 2D coupling terms:")
    for order, lines in sorted(by_order.items()):
        fname = os.path.join(args.outdir, f"f{order}{args.molecule}.dat")
        # Append to existing file (1D terms already there)
        with open(fname, "a") as fout:
            for mi, p, mj, q, c in lines:
                indices = " ".join([str(mi)]*p + [str(mj)]*q)
                fout.write(f"  {indices}    {c:.10f}d0\n")
        print(f"    Appended {len(lines)} terms to {fname}")

    print(f"\n  Done. 2D coupling SOP conversion complete.")


if __name__ == "__main__":
    main()
