#!/usr/bin/env python
import sys, numpy as np # type: ignore

def readNWFC(outfile, nm) :
    print("Reading harmonic force constants from file: %s" %(outfile))
    with open(outfile, 'r') as ofile:
       
        # Find section containing harmonic force constants
        for line in ofile :
            if "(Projected Frequencies expressed in cm-1)" in line:
                print("Found NWChem harmonic force constants in file: %s" %(outfile))
                break
        
        freqs = []
        rows = []
        for line in ofile:
            if "----------------------------------------------------------------------------" in line:
                print("Finished reading NWChem harmonic force constants from file: %s" %(outfile))
                break
            
            # Read in values
            if "P.Frequency" in line :
                vals = line.split()
                for val in vals[1:]:
                    freqs.append(float(val))
                next(ofile)
                continue
            
            if line.strip() :
                vals = line.split()
                if len(rows) < int(vals[0]) :
                    rows.append(vals[1:])
                else :    
                    for val in vals[1:]:
                        rows[int(vals[0])-1].append(float(val))
            
            if not line.strip() :
                next(ofile)
                next(ofile)
                continue
    
    rows = np.array(rows, dtype=float)
    nmodes = rows.T
    with open("./nwc_nmodes_"+str(nm)+".dat", 'w') as nmfile :
        i = 0
        for freq in freqs:
            if freq > 0 :
                nmfile.write(f"{freq:<15.6f} ")
                for entry in nmodes[i]:
                    nmfile.write(f"{entry:<15.6f} ")
                nmfile.write("\n")
                i += 1                

# $ nwchem_fc.py <nwchem.out> <system name>
print("Running nwchem_fc.py to read force constants from file: %s" %(sys.argv[1]))
outfile = sys.argv[1]
nm = sys.argv[2]
readNWFC(outfile, nm)