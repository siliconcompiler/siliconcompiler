# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging
import argparse
import os
import re
import json
import sys
import importlib.resources

#Shorten siliconcompiler as sc
import siliconcompiler as sc
from siliconcompiler.schema import schema

###########################
def cmdline():
    '''Handles the command line configuration usign argparse. 
    All configuration parameters are exposed at the command line interface.
    This is outside of the class since this can be called 

    '''
    def_cfg = schema()

    os.environ["COLUMNS"] = '100'

    # Argument Parser
    
    parser = argparse.ArgumentParser(prog='sc',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SC)")

    # Required positional source file argument
    parser.add_argument('sc_source',
                        nargs='+',
                        help=def_cfg['sc_source']['help'])

    # Auto generated source file arguments
    for key1 in sorted(def_cfg):
        print(key1)
        #Library and macro pattern        
        if key1 in ('sc_stdlib', 'sc_macro'):
            for key2 in  def_cfg[key1]['default'].keys():
                #Timing/power has a fixed structure with default as keyword for lib/corner
                if 'default' in def_cfg[key1]['default'][key2]:   
                    if key2 in ('cells'):
                        metahelp = '<lib type cellname>'
                    else:
                        metahelp = '<lib type filepath>'
                    parser.add_argument(def_cfg[key1]['default'][key2]['default']['switch'],
                                        dest=key1+"_"+key2,
                                        metavar=metahelp,
                                        action='append',
                                        help=def_cfg[key1]['default'][key2]['default']['help'],
                                        default = argparse.SUPPRESS)
                else:
                    print(key1, key2, def_cfg[key1]['default'][key2]['type'])
                    if (def_cfg[key1]['default'][key2]['type'][0] == 'file'): 
                        metahelp = '<lib filepath>'
                    else:
                        metahelp = '<lib string>'
                    parser.add_argument(def_cfg[key1]['default'][key2]['switch'],
                                        dest=key1+"_"+key2,
                                        metavar=metahelp,
                                        action='append',
                                        help=def_cfg[key1]['default'][key2]['help'],
                                        default = argparse.SUPPRESS)        

        #MCMM pattern
        elif key1 in ('sc_mcmm'):
            for key2 in def_cfg[key1]['default'].keys():
                parser.add_argument(def_cfg[key1]['default'][key2]['switch'],
                                    dest=key1+"_"+key2,
                                    metavar='<mode ' + key2 + '>',
                                    action='append',
                                    help=def_cfg[key1]['default'][key2]['help'],
                                    default = argparse.SUPPRESS)             
        #Tool pattern
        elif key1 in ('sc_tool'):
            for key2 in def_cfg['sc_tool']['syn'].keys():
                parser.add_argument(def_cfg[key1]['syn'][key2]['switch'],
                                    dest=key1+"_"+key2,
                                    metavar='<stage ' + key2 + '>',
                                    action='append',
                                    help=def_cfg[key1]['syn'][key2]['help'],
                                    default = argparse.SUPPRESS)
        #Command line on/off switches
        elif def_cfg[key1]['type'] == "bool":
            parser.add_argument(def_cfg[key1]['switch'],
                                dest=key1,
                                action='store_true',
                                help=def_cfg[key1]['help'],
                                default = argparse.SUPPRESS)
        #Flat config structure pattern
        elif key1 != "sc_source":
            parser.add_argument(def_cfg[key1]['switch'],
                                dest=key1,
                                action='append',
                                help=def_cfg[key1]['help'],
                                default = argparse.SUPPRESS)
                                

    #Parsing args and converting to dict
    cmdargs = vars(parser.parse_args())

    # Copying flat parse_args to nested cfg dict based on key type
    # Values are lists of varying legnth based on cfg parameter
    # stdlib, macro, tool has length 3 or 4 depending on type
    # (timing, cells, power has length 4)
    # Format is "key(s) val"

    #scalars, list, lists of lists need to be treated
    #destination is the nested cfg dictionary

    cfg= {}
    
    for key,all_vals in cmdargs.items():
       
        switch = key.split('_')       
        param = switch[0] + "_" + switch[1]
        if param not in cfg:
            cfg[param] = {}

        #Iterate over list since these are dynamic
        if switch[1] in ('stdlib', 'macro', 'tool'):
            for val in all_vals:
                if val[0] not in cfg[param]:
                        cfg[param][val[0]]={}
                if switch[2] not in cfg[param][val[0]].keys():
                        cfg[param][val[0]][switch[2]] = {}
                if switch[2] in ('timing', 'power', 'cells'):
                    if val[1] not in cfg[param][val[0]][switch[2]].keys():
                        cfg[param][val[0]][switch[2]][val[1]]={}
                        cfg[param][val[0]][switch[2]][val[1]]['value'] = val[2]
                    else:
                        cfg[param][val[0]][switch[2]][val[1]]['value'].extend(val[2])
                else:
                    if 'value' not in cfg[param][val[0]][switch[2]].keys():
                        cfg[param][val[0]][switch[2]]['value'] = val[1]
                    else:
                        cfg[param][val[0]][switch[2]]['value'].extend(val[1])
        else:
            if 'value' not in cfg:
                 cfg[param] = {}
                 cfg[param]['value'] = all_vals

            else:
                cfg[param]['value'].extend(all_vals)

    return cfg


###########################
def main():

    scriptdir = os.path.dirname(os.path.abspath(__file__))
    rootdir = re.sub("siliconcompiler/siliconcompiler", "siliconcompiler", scriptdir, 1)
    pdkcfg = rootdir + "/pdklib/virtual/nangate45/nangate45.json"
    ipcfg = rootdir + "/iplib/virtual/nangate45/NangateOpenCellLibrary.json"
    edacfg = rootdir + "/edalib/asic/sc_asicflow.json"


    #Command line inputs, read once
    cmdlinecfg = cmdline()

    #Create one (or many...) instances of Chip class
    mychip = sc.Chip()
    
    # Reading in default config files unless cfg file is set
    if 'nangate45' in cmdlinecfg['sc_target']['value']:
        mychip.readcfg(edacfg)
        mychip.readcfg(pdkcfg)
        mychip.readcfg(ipcfg)
    
    # Reading in user variables
    mychip.readenv()

    # Reading in command line arguments
    mychip.mergecfg(cmdlinecfg)
    
    #Resolve as absolute paths (should be a switch)
    mychip.abspath()

    #Creating hashes for all sourced files
    #mychip.hash()

    #Lock chip configuration
    mychip.lock()
    
    #Printing out run-config
    mychip.writecfg("sc_setup.json")

    all_stages = mychip.get('sc_stages')
    for stage in all_stages:
        mychip.run(stage)
    
    
#########################
if __name__ == "__main__":    
    sys.exit(main())
