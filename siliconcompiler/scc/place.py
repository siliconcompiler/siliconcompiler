# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import json
import os
import sys



#Directories should be absolute paths
def place(config_file, input_dir, output_dir):

    #Read scc_args from json file
    with open(os.path.abspath(config_file), "r") as f:
        scc_args = json.load(f)

    #Moving to working directory
    cwd = os.getcwd()
    os.makedirs(os.path.abspath(output_dir), exist_ok=True)
    os.chdir(os.path.abspath(output_dir))

    #Dump TCL (EDA tcl lacks support for json)
    dumptcl(scc_args, "scc_setup.tcl")

    #Execute EDA tool
    os

    error = subprocess.run(cat_cmd, shell=True)
    
    #Return to CWD
    os.chdir(cwd)

    
def dumptcl(scc_args, filename):
    print("wow")
    with open(filename, 'w') as f:
        for key in sorted(scc_args.keys()):
            print('set ', key , scc_args[key], file=f)

##############################################
#TESTING
place("setup.json", "indir","outdir")
