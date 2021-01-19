# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging
import argparse
import os

#Shorten siliconcompiler as sc
import siliconcompiler as sc
from siliconcompiler.config import defaults

###########################
def cmdline():
    '''Handles the command line configuration usign argparse. 
    All configuration parameters are exposed at the command line interface.

    '''
    default_cfg = defaults()

    os.environ["COLUMNS"] = '100'

    # Argument Parser
    
    parser = argparse.ArgumentParser(prog='siliconcompiler',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SC)")

    # Source files
    parser.add_argument('sc_source',
                        nargs='+',
                        help=default_cfg['sc_source']['help'])

    # All other arguments
    for key in default_cfg.keys():
        print(key)
        if default_cfg[key]['type'] is "nested":
            for subkey in  default_cfg[key]['help']:
                parser.add_argument(default_cfg[key]['switch'][subkey],
                                    dest=key+"_"+subkey,
                                    action='append',
                                    help=default_cfg[key]['help'][subkey])   
        elif default_cfg[key]['type'] is "bool":
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                action='store_true',
                                help=default_cfg[key]['help'])
        elif default_cfg[key]['type'] in {"int", "float", "string"}:
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                help=default_cfg[key]['help'])
        elif key != "sc_source":
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                action='append',
                                help=default_cfg[key]['help'])

    args = parser.parse_args()

    return args


###########################
def main():

    #Command line interface
    cmdargs = cmdline()

    #Create one (or many...) instances of Chip class
    chip = sc.Chip(cmdargs)

    #Custom config code goes here

    #Creating hashes for all sourced files
    chip.hash()

    #Lock chip configuration
    chip.lock()
    
    #Printing out run-config
    chip.writecfg("sc_setup.json")

    #Compiler
    chip.run("import")
    chip.run("syn")
    chip.run("floorplan")
    chip.run("place")
    chip.run("cts")
    chip.run("route")
    chip.run("signoff")
    chip.run("export")
    
#########################
if __name__ == "__main__":    
    sys.exit(main())
