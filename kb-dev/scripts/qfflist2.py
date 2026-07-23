#!/usr/bin/env python
import sys

def readFC2(outfile, nm) :
    print("Reading harmonic force constants from file: %s" %(outfile))
    with open(outfile, 'r') as ofile:
       with open("f2"+str(nm)+".dat", 'w') as f2file:
           for line in ofile:
               if "Harmonic force constants (cm-1)" in line:
                  print("Found harmonic force constants in file: %s" %(outfile))
                  break
           for line in ofile:
                if any(c.isalpha() for c in line):
                    print("Finished reading harmonic force constants from file: %s" %(outfile))
                    break
                vals = line.split()
                for val in vals:
                    f2file.write(f"{val:4} ")
                f2file.write("\n")

def readFC3(outfile, nm) :
    print("Reading cubic force constants from file: %s" %(outfile))
    with open(outfile, 'r') as ofile:
       with open("f3"+str(nm)+".dat", 'w') as f3file:
           for line in ofile:
               if "Non-zero cubic force constants (cm-1)" in line:
                  print("Found cubic force constants in file: %s" %(outfile))
                  break
           for line in ofile:
                if any(c.isalpha() for c in line):
                    print("Finished reading cubic force constants from file: %s" %(outfile))
                    break
                vals = line.split()
                for val in vals:
                    f3file.write(f"{val:4} ")
                f3file.write("\n")

def readFC4(outfile, nm) :
    print("Reading quartic force constants from file: %s" %(outfile))
    with open(outfile, 'r') as ofile:
       with open("f4"+str(nm)+".dat", 'w') as f4file:
           for line in ofile:
               if "Non-zero quartic force constants (cm-1)" in line:
                  print("Found quartic force constants in file: %s" %(outfile))
                  break
           for line in ofile:
                if any(c.isalpha() for c in line):
                    print("Finished reading quartic force constants from file: %s" %(outfile))
                    break
                vals = line.split()
                for val in vals:
                    f4file.write(f"{val:4} ")
                f4file.write("\n")

# $ qfflist2.py <pbqff.out> <system name>
print("Running qfflist2.py to read force constants from file: %s" %(sys.argv[1]))
outfile = sys.argv[1]
nm = sys.argv[2]
readFC2(outfile, nm)
readFC3(outfile, nm)
readFC4(outfile, nm)