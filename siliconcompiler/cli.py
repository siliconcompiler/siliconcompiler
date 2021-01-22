# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging
import argparse
import os
import json

#Shorten siliconcompiler as sc
import siliconcompiler as sc
from siliconcompiler.config import defaults

###########################
def cmdline():
    '''Handles the command line configuration usign argparse. 
    All configuration parameters are exposed at the command line interface.
    This is outside of the class since this can be called 

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
                if key2 in ('timing', 'power', 'cells'):
                    parser.add_argument(def_cfg[key1]['default'][key2]['default']['switch'],
                                        dest=key1+"_"+key2,
                                        action='append',
                                        help=def_cfg[key1]['default'][key2]['default']['help'])
                #Cells have a variable number of types
                else:
                    parser.add_argument(def_cfg[key1]['default'][key2]['switch'],
                                        dest=key1+"_"+key2,
                                        action='append',
                                        help=def_cfg[key1]['default'][key2]['help'])
        elif key1 in ('sc_tool'):
            # Using 'syn' tool as template for all configs
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

    #Parsing args and converting to dict        
    cmdargs = vars(parser.parse_args())

    # Copying flat parse_args to nested cfg dict based on key type
    # Values are lists of varying legnth based on cfg parameter
    # stdlib, macro, tool has length 3 or 4 depending on type
    # (timing, cells, power has length 4)
    # Format is "keys val"
    cfg= {}
    for key,values in cmdargs.items():
        if values != None:
            #split string and command switch
            switch = key.split('_')       
            # Nested dict entries
            param = switch[0] + "_" + switch[1]
            if param not in cfg:
                cfg[param] = {}
            #Iterate over list
            if type(values) is list:
                for val in values:
                    #TODO: Any way to simplify init of these dicts?
                    if switch[1] in ('stdlib', 'macro', 'tool'):
                        #All these i
                        field = val.split(' ')
                        if field[0] not in cfg[param]:
                            cfg[param][field[0]]={}
                        if switch[2] not in cfg[param][field[0]].keys():
                            cfg[param][field[0]][switch[2]]={}
                        if switch[2] in ('timing', 'power', 'cells'):
                            if switch[2] not in cfg[param][field[0]][switch[2]].keys():
                                cfg[param][field[0]][switch[2]][field[1]]={}
                            cfg[param][field[0]][switch[2]][field[1]]['value'] = field[2]
                        else:
                            if field[1].isdigit():
                                cfg[param][field[0]][switch[2]]['value']= int(field[1])
                            else:
                                cfg[param][field[0]][switch[2]]['value']= field[1]
                        # Check for boolean switches that are true
                    else:
                        cfg[param] = val   
            else:
                cfg[param] = values   
                
    return cfg


###########################
def main():

    #Command line inputs, read once
    cmdcfg = cmdline()

    print(json.dumps(cmdcfg, sort_keys=True, indent=4))
    
    #Create one (or many...) instances of Chip class
    mychip = sc.Chip()

    # Iterative over nested dict recursively to get environment variables
    mychip.readenv()

    # Read files sourced from command line
    #for filename in cmdargs['sc_cfgfile']:
    #    mychip.loadcfg(file=filename)
    
    # Copy a cfg dictionary into Chip.cfg
    #mychip.copycfg(cmdcfg)
        
    #Resolve as absolute paths (should be a switch)
    #mychip.abspath()

    #Creating hashes for all sourced files
    #mychip.hash()

    #Lock chip configuration
    mychip.lock()
    
    #Printing out run-config
    mychip.writecfg("sc_setup.json")

    #Compilation
    #for stage in mychip.get('sc_stages'):
    mychip.run("import")
    
#########################
if __name__ == "__main__":    
    sys.exit(main())
