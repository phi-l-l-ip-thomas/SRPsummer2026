#!/usr/bin/env python3
import sys, numpy as np
from scipy.optimize import linear_sum_assignment

# Read normal modes into the pipeline
def read_nwc_nmodes(nm):
    with open(f"../nwchem/nwc_nmodes_{nm}.dat", 'r') as nwcfile :
        nwc_freqs = []
        nwc_nmodes = []
        for line in nwcfile :
            vals = line.split()
            nwc_freqs.append(float(vals[0]))
            nwc_nmodes.append(vals[1:])
        nwc_nmodes = np.array(nwc_nmodes, dtype=float)
    return nwc_freqs, nwc_nmodes.T

def read_pbqff_nmodes(nm):
    with open(f"../pbqff/pbqff2_nmodes_{nm}.dat", 'r') as pbqff2file :
        pbqff2_freqs = []
        pbqff2_nmodes = []
        for line in pbqff2file :
            vals = line.split()
            pbqff2_freqs.append(float(vals[0]))
            pbqff2_nmodes.append(vals[1:])
        pbqff2_nmodes = np.array(pbqff2_nmodes, dtype=float)
    return pbqff2_freqs, pbqff2_nmodes.T

# Read NWChem and PBQFF geometries into the pipeline
def read_nwc_geometry(nm) :
    nwc_points = []
    with open(f"../nwchem/nwc_{nm}.out", 'r') as nwcfile:
        print("Reading NWChem geometry from file: %s" %(nwcfile))
        # Find section containing harmonic force constants
        for line in nwcfile :
            if "Optimization converged" in line:
                print("Found NWChem optimization in file: %s" %(nwcfile))
                break
        for line in nwcfile :
            if "Output coordinates in angstroms (scale by  1.889725989 to convert to a.u.)" in line:
                while "---- ---------------- ---------- -------------- -------------- --------------" not in line:
                    line = next(nwcfile)
                print("Found NWChem optimized geometry in file: %s" %(nwcfile))
                break

        for line in nwcfile:
            if not line.strip() :
                print("Finished reading NWChem geometry from file: %s" %(nwcfile))
                break
            
            # Read in values
            vals = line.split()
            nwc_points.append(vals[3:])

    nwc_points = np.array(nwc_points, dtype=float)
    return nwc_points

def read_pbqff_geometry(nm) :
    pbqff_points = []
    with open(f"../pbqff/pbqff.out", 'r') as pbqfffile:
        print("Reading PBQFF geometry from file: %s" %(pbqfffile))
        # Find section containing harmonic force constants
        for line in pbqfffile :
            if "Geometry:" in line:
                print("Found PBQFF optimized geometry in file: %s" %(pbqfffile))
                break

        for line in pbqfffile:
            if not line.strip() :
                print("Finished reading PBQFF geometry from file: %s" %(pbqfffile))
                break

            # Read in values
            vals = line.split()
            pbqff_points.append(vals[1:])

    pbqff_points = np.array(pbqff_points, dtype=float)
    return pbqff_points

def kabsch_numpy(P, Q): # from https://hunterheidenreich.com/posts/kabsch-algorithm/
    """
    Computes the optimal rotation and translation to align two sets of points (P -> Q),
    and their RMSD.

    :param P: A Nx3 matrix of points
    :param Q: A Nx3 matrix of points
    :return: A tuple containing the optimal rotation matrix, the optimal
             translation vector, and the RMSD.
    """
    assert P.shape == Q.shape, "Matrix dimensions must match"

    # Compute centroids
    centroid_P = np.mean(P, axis=0)
    centroid_Q = np.mean(Q, axis=0)

    # Center the points
    p = P - centroid_P
    q = Q - centroid_Q

    # Compute the covariance matrix
    H = np.dot(p.T, q)

    # SVD
    U, S, Vt = np.linalg.svd(H)

    # Validate right-handed coordinate system
    if np.linalg.det(np.dot(Vt.T, U.T)) < 0.0:
        Vt[-1, :] *= -1.0

    # Optimal rotation
    R = np.dot(Vt.T, U.T)

    # Optimal translation (depends on R, so computed after it)
    t = centroid_Q - np.dot(R, centroid_P)

    # RMSD
    rmsd = np.sqrt(np.sum(np.square(np.dot(p, R.T) - q)) / P.shape[0])

    return R, t


def map_nwc_to_pbqff(nwc_points, pbqff_points, nwc_freqs, nwc_nmodes, pbqff_nmodes):
    np.set_printoptions(precision=6, suppress=True, linewidth=120)
    R, t = kabsch_numpy(nwc_points, pbqff_points)
    R = np.kron(np.eye(len(nwc_points)), R)
    nwc_nmodes = R @ nwc_nmodes
    for i in range(len(nwc_nmodes)) :
        nwc_nmodes[i] += t[i%3]
    
    # Match normal modes using Cross-Correlation + Hungarian algorithm
    C = nwc_nmodes.T @ pbqff_nmodes
    C /= np.linalg.norm(nwc_nmodes)
    C /= np.linalg.norm(pbqff_nmodes)

    rows, cols = linear_sum_assignment(-C)
    
    # CHECK THIS WITH GOOD DATA
    print(nwc_freqs)
    print(nwc_nmodes)
    print(pbqff_nmodes)
    print(C)
    print()
    print(nwc_nmodes)
    print(nwc_freqs)
    print()
    print(cols)
    nwc_nmodes = np.array([nwc_nmodes.T[i] for i in cols]).T
    nwc_freqs = np.array([nwc_freqs[i] for i in cols])
    print(nwc_nmodes)
    print(nwc_freqs)

    return nwc_freqs, nwc_nmodes

# Execute data processing
# $translation.py <system name>
nwc_freqs, nwc_nmodes = read_nwc_nmodes(sys.argv[1])
pbqff2_freqs, pbqff2_nmodes = read_pbqff_nmodes(sys.argv[1])

nwc_points = read_nwc_geometry(sys.argv[1])
pbqff_points = read_pbqff_geometry(sys.argv[1])
print(f"nwc_points: {nwc_points.shape[0]}")
print(f"pbqff_points: {pbqff_points.shape[0]}")
print()
nwc_freqs, nwc_nmodes = map_nwc_to_pbqff(nwc_points, pbqff_points, nwc_freqs, nwc_nmodes, pbqff2_nmodes)

# Generate matched NWChem normal modes file for use in MLCP
with open("../nwchem/nwcf2"+str(sys.argv[1])+".dat", 'w') as f2file :
    print("Generating final harmonic FCs...")
    mode = 1
    for freq in nwc_freqs:
        if freq > 0 :
            f2file.write(f"{mode:<4} {mode:<4} {freq}\n")
            mode += 1
