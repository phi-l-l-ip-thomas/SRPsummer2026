#!/usr/bin/env python3
import sys

# Read in input parameters
def read_input(input_file) :
    print("Reading input parameters from file: %s" %(input_file))
    
    params = {}
    with open(input_file, 'r') as infile :
        lines = iter(infile)
        for line in lines :
            line = line.strip()

            if ((not line or line.startswith("#")) and not line.startswith("# Geometry") and 
                not line.startswith("# PBQFF Input") and not line.startswith("# NWChem Input") and
                not line.startswith("# MLCP Input") and not line.startswith("# Intder.in")) :
                continue

            # System Name
            if 'system_name' in line :
                key, value = map(str.strip, line.split("=", 1))
                
                params['system_name'] = value
            
            # Geometry block
            if '# Geometry' in line :
                block = []
                for line in lines:
                    if line.strip() == '--':
                        break
                    block.append(line.rstrip())

                params['geometry'] = "\n".join(block)
            
            # PBQFF block
            if '# PBQFF Input' in line :
                block = []
                for line in lines:
                    if line.strip() == '--':
                        break
                    block.append(line.rstrip())

                params['pbqff_params'] = "\n".join(block)

            if '# Intder.in' in line :
                block = []
                for line in lines:
                    if line.strip() == '--':
                        break
                    block.append(line.rstrip())

                params['intder.in'] = "\n".join(block)

            # NWChem block
            if '# NWChem Input' in line :
                block = []
                for line in lines:
                    if line.strip() == '--':
                        break
                    block.append(line.rstrip())

                params['nwc_params'] = "\n".join(block)

            # MLCP block
            if '# MLCP Input' in line :
                block = []
                for line in lines:
                    if line.strip() == '--':
                        break
                    block.append(line.rstrip())

                params['mlcp_params'] = "\n".join(block)
    return params

# Generate PBQFF input file
def generate_pbqff_input(params) :
    print('Generating PBQFF input file')
    system_name = params['system_name']
    with open(f'./{system_name}.toml', 'w') as toml :
        toml.write(f"geometry=\"\"\"\n{params['geometry']}\n\"\"\"\n")
        toml.write(params['pbqff_params'])
    with open(f'./intder.in', 'w') as intder :
        intder.write(params['intder.in'])


# Generate NWChem input file
def generate_nwc_input(params) :
    print('Generating NWChem input file')
    system_name = params['system_name']
    with open(f'./{system_name}.nw', 'w') as nw :
        nw.write(f"START {system_name}\ngeometry units angstroms\n{params['geometry']}\nEND\n")
        nw.write(params['nwc_params'])

# Generate MLCP input file
def generate_mlcp_input(params) :
    print('Generating MLCP input file')
    system_name = params['system_name']
    with open(f'./mlcp_{system_name}.inp', 'w') as mlcp :
        mlcp.write(params['mlcp_params'])

# Execute file generation
params = read_input(sys.argv[1])
generate_pbqff_input(params)
generate_nwc_input(params)
generate_mlcp_input(params)