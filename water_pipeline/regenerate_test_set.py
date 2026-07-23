"""
Run ON PERLMUTTER. Regenerates nwchem_test_set/*.nw using the VALIDATED
NWChem equilibrium geometry + eigenvectors from h2o_opt.out (RHF/STO-3G),
displacing along each mode by explicit step_bohr values.

This deliberately does NOT try to reverse-engineer the old filename-label
convention (e.g. "stepm1p5811") -- that mapping is unrecoverable without the
original generator script. Instead, step_bohr values are specified directly
and unambiguously, matching the same physical range as your training data
(nwchem_mode{N}_expensive.dat goes up to +/-1.649 bohr).

Validated against your existing mode1 test file: solving directly for the
displacement that reproduces the real geometry gives step_bohr=-1.64199,
matching this exact mechanism (equilibrium geometry + eigenvector + linear
displacement) to 6 significant figures across all nonzero coordinates.
"""

import os
import numpy as np

BOHR_TO_ANGSTROM = 0.529177

# --- validated equilibrium geometry (RHF/STO-3G, from h2o_opt.out) ---
GEOMETRY_ANGSTROM = np.array([
    [0.0,         0.0,  -0.04280778],   # O
    [0.75806363,  0.0,  -0.67859611],   # H1
    [-0.75806363, 0.0,  -0.67859611],   # H2
])
ATOM_LABELS = ["O", "H", "H"]

# --- validated frequencies and eigenvectors (from h2o_opt.out, P.Frequency block) ---
FREQUENCIES_CM1 = [2170.02, 4140.26, 4391.32]  # mode 1, 2, 3

# eigenvector rows: O_x,O_y,O_z, H1_x,H1_y,H1_z, H2_x,H2_y,H2_z (columns 7,8,9)
NORMAL_MODES = {
    1: np.array([0.00000, 0.00000, 0.06612, -0.43141, 0.00000, -0.52470,
                 0.43141, 0.00000, -0.52470]).reshape(3, 3),
    2: np.array([-0.00000, 0.00000, 0.05123, 0.55678, 0.00000, -0.40655,
                 -0.55678, 0.00000, -0.40655]).reshape(3, 3),
    3: np.array([0.06562, 0.00000, -0.00000, -0.52076, 0.00000, 0.43676,
                 -0.52076, 0.00000, -0.43676]).reshape(3, 3),
}

# mode character, confirmed from eigenvector symmetry -- useful for your
# tanh (symmetric) vs Morse (asymmetric) SOP decision:
#   mode 1: symmetric (bend)             -> tanh
#   mode 2: symmetric (symmetric stretch) -> tanh
#   mode 3: asymmetric (asym. stretch)    -> Morse

MOPAC_LIKE_HEADER = """TITLE "h2o_mode{mode}_test_{label}"

BASIS
H library sto-3g
O library sto-3g
END

SCF
rhf
PRINT low
END

geometry units angstrom
{geom_lines}
end

TASK scf gradient
"""


def displace(geometry, vec, step_bohr):
    return geometry + (step_bohr * BOHR_TO_ANGSTROM) * vec


def format_label(step_bohr):
    """e.g. -1.649 -> 'stepm1p6490', 0.3298 -> 'stepp0p3298' (matches your
    original naming convention's sign/decimal style, but now the number in
    the filename IS the literal, exact step_bohr -- no hidden conversion)."""
    sign = "m" if step_bohr < 0 else "p"
    return f"step{sign}{abs(step_bohr):.4f}".replace(".", "p")


def write_nw(mode, step_bohr, outdir):
    vec = NORMAL_MODES[mode]
    geom = displace(GEOMETRY_ANGSTROM, vec, step_bohr)
    geom_lines = "\n".join(
        f"  {lbl}      {xyz[0]:.10f}      {xyz[1]:.10f}      {xyz[2]:.10f}"
        for lbl, xyz in zip(ATOM_LABELS, geom)
    )
    label = format_label(step_bohr)
    content = MOPAC_LIKE_HEADER.format(mode=mode, label=label, geom_lines=geom_lines)
    fname = f"h2o_mode{mode}_test_{label}_grad.nw"
    path = os.path.join(outdir, fname)
    with open(path, "w") as f:
        f.write(content)
    return path


def main(outdir="nwchem_test_set_v2", modes=(1, 2, 3), n_points=15,
         step_max=1.65, seed=42):
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(seed)

    # same step_bohr grid used for all 3 modes -- makes cross-mode
    # comparison meaningful, and stays within your training data's range
    # (nwchem_mode{N}_expensive.dat spans +/-1.649 bohr)
    steps = np.sort(rng.uniform(-step_max, step_max, n_points))
    # ensure 0.0 is included (equilibrium sanity check point)
    steps = np.concatenate([steps, [0.0]])

    print(f"Regenerating test set: {len(steps)} points x {len(modes)} modes "
          f"= {len(steps) * len(modes)} .nw files in {outdir}/")
    print(f"step_bohr values: {np.round(steps, 4).tolist()}")

    for mode in modes:
        for step in steps:
            path = write_nw(mode, step, outdir)
        print(f"  mode {mode}: wrote {len(steps)} files")

    print(f"\nDone. Next: submit these through NWChem the same way you ran "
          f"the original nwchem_test_set/ (same .nw -> SCF gradient job), "
          f"then re-run load_test_data.py pointed at '{outdir}' instead of "
          f"'nwchem_test_set'.")


if __name__ == "__main__":
    main()
