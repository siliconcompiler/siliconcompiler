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
    def_cfg = defaults()

    os.environ["COLUMNS"] = '100'

    # Argument Parser
    
    parser = argparse.ArgumentParser(prog='sc',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SC)")

    # Source files
    parser.add_argument('sc_source',
                        nargs='+',
                        help=def_cfg['sc_source']['help'])

    # All other arguments
    for key1 in sorted(def_cfg):
        if key1 in ('sc_stdlib', 'sc_macro'):
            for key2 in  def_cfg[key1]['default'].keys():
                #Timing/power has a fixed structure with default as keyword for lib/corner
                if key2 in ('timing', 'power'):
                    parser.add_argument(def_cfg[key1]['default'][key2]['default']['switch'],
                                        dest=key1+"_"+key2,
                                        action='append',
                                        help=def_cfg[key1]['default'][key2]['default']['help'])
                #Cells have a variable number of types
                elif key2 in ('cells'):
                    for key3 in def_cfg[key1]['default'][key2].keys():
                        parser.add_argument(def_cfg[key1]['default'][key2][key3]['switch'],
                                            dest=key1+"_"+key3,
                                            action='append',
                                            help=def_cfg[key1]['default'][key2][key3]['help'])
                else:
                    parser.add_argument(def_cfg[key1]['default'][key2]['switch'],
                                        dest=key1+"_"+key2,
                                        action='append',
                                        help=def_cfg[key1]['default'][key2]['help'])
        elif key1 in ('sc_tool'):
            # Using sun tool as template for all configs
            for key2 in def_cfg['sc_tool']['syn'].keys():           
                parser.add_argument(def_cfg[key1]['syn'][key2]['switch'],
                                    dest=key1+"_"+key2,
                                    action='append',
                                    help=def_cfg[key1]['syn'][key2]['help'])   
        elif def_cfg[key1]['type'] is "bool":
            parser.add_argument(def_cfg[key1]['switch'],
                                dest=key1,
                                action='store_true',
                                help=def_cfg[key1]['help'])
        elif def_cfg[key1]['type'] in {"int", "float", "string"}:
            parser.add_argument(def_cfg[key1]['switch'],
                                dest=key1,
                                help=def_cfg[key1]['help'])
        elif key1 != "sc_source":
            parser.add_argument(def_cfg[key1]['switch'],
                                dest=key1,
                                action='append',
                                help=def_cfg[key1]['help'])

    args = parser.parse_args()

    return args


###########################
def main():

    #Command line interface
    cmdargs = cmdline()

    #Create one (or many...) instances of Chip class
    chip = sc.Chip(cmdargs)

    # Iterative over nested dict recursively to get environment variables
    readenv(self.cfg)

    #Custom config code goes here

             
    # setting up an empty status dictionary for each stage
    self.status = {}
    for stage in self.cfg['sc_stages']['default']:
        self.status[stage] = ["idle"]

    #Overide with command line arguments
    if cmdargs is not None:
        self.readargs(cmdargs)
        
    #Resolve all source files as absolute paths (should be a switch)
    self.abspath()
    
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
