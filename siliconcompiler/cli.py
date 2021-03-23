# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging
import argparse
import os
import re
import json
import sys
import uuid
import importlib.resources
from argparse import RawTextHelpFormatter

#Shorten siliconcompiler as sc
import siliconcompiler as sc
from siliconcompiler.setup  import setup_target
from siliconcompiler.schema import schema_cfg
from siliconcompiler.client import remote_run

###########################
def cmdline():
    '''Handles the command line configuration usign argparse. 
    All configuration parameters are exposed at the command line interface.
    This is outside of the class since this can be called 

    '''
    def_cfg = schema_cfg()

    os.environ["COLUMNS"] = '80'

    # Argument Parser

    sc_description = '\n'.join([
    "-----------------------------------------------------------------------",
    "Silicon Compiler Collection (SC)                                       ",
    "                                                                       ",
    "The SC architecture describes the command line and API arguments that  ",
    "form the basis of a foundry and eda agnostic silicon compilation flow  ",
    "Short switch arguments are specified as <type>, where type can be      ",
    "str, file, num, bool. Some switches have compelx inputs in which case  ",
    "the argument type is specified as <> and tha description is found in   ",
    "the switch help paragraph. Complete documentation can be found at in   ",
    "user manual. A few examples are included here to demonstrate simple use",
    "cases.                                                                 ",
    "                                                                       ",
    "Examples:                                                              ",
    "$ sc 'hello_world.v' -target freepdk45'                                ",
    "$ sc 'my_riscv_cpu.v' -target asap7 -design my_riscv_cpu               ",
    "$ sc 'my_tpu.v' -cfgfile my_tpu_setup.json                             ",
    "                                                                       ",  
    "-----------------------------------------------------------------------"])

    
    
    parser = argparse.ArgumentParser(prog='sc',
                                     formatter_class =lambda prog: RawTextHelpFormatter(prog, indent_increment=1, max_help_position=23),
                                     prefix_chars='-+',
                                     description=sc_description)

    
    #formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
    # Required positional source file argument
    parser.add_argument('source',
                        nargs='+',
                        help=def_cfg['source']['short_help'])

    #Recursive argument adder
    add_arg(def_cfg, parser)
    
    #Parsing args and converting to dict
    cmdargs = vars(parser.parse_args())

    # Copying flat parse_args to nested cfg dict based on key type
    # Values are lists of varying legnth based on cfg parameter
    # stdlib, macro, tool has length 3 or 4 depending on type
    # (timing, cells, power has length 4)
    # Format is "key(s) val"
    # scalars, list, lists of lists need to be treated
    # destination is the nested cfg dictionary

    cfg= {}

    for key,all_vals in cmdargs.items():
        # Nested parameters
        # ['stdcells'][lib]['lef']
        # ['flow'][step]['exe']
        # ['goal'][step]['hold_tns']
        m = re.match('(stdcells|macro|flow|real|goal)_(.*)', key)
        #TODO: need to do this properly with search function to populate
        # param when not found!
        if m:
            param0 = m.group(1)
            param2 = m.group(2)            
            if param0 not in cfg:
                cfg[param0] = {}
            for entry in all_vals:
                #splitting command line tuple inputs
                val = entry.split(' ')
                if val[0] not in cfg[param0]:
                    cfg[param0][val[0]]={}
                if param2 not in cfg[param0][val[0]].keys():
                    cfg[param0][val[0]][param2] = {}
                if param2 in ('timing', 'power', 'cells'):
                    if val[1] not in cfg[param0][val[0]][param2].keys():
                        cfg[param0][val[0]][param2][val[1]]={}
                        cfg[param0][val[0]][param2][val[1]]['value'] = [val[2]]
                    else:
                        cfg[param0][val[0]][param2][val[1]]['value'].extend(val[2])
                else:
                    if 'value' not in cfg[param0][val[0]][param2].keys():
                        cfg[param0][val[0]][param2]['value'] = [val[1]]
                    else:
                        cfg[param0][val[0]][param2]['value'].extend(val[1])
        
        else:
            #Flat parameters
            if 'value' not in cfg:
                 cfg[key] = {}
                 cfg[key]['value'] = all_vals

            else:
                cfg[key]['value'].extend(all_vals)

    return cfg

###########################
def add_arg(cfg, parser, keys=None):
    ''' Recursively add command line arguments from cfg dictionary
    '''
    #TODO: fix properly with command line check
    longhelp = False
    if keys is None:
        keys = []
    for k,v in sorted(cfg.items()):
        #print(k)
        #No command line switches for these odd balls
        if k in ('source'):
            pass
        #Optimizing command line switches for these
        elif k in ('flow', 'goal', 'real'):
            for k2 in cfg[k]['default'].keys():
                helpstr = cfg[k]['default'][k2]['short_help']
                if longhelp:
                    helpstr = (helpstr +
                               '\n\n' +
                               '\n'.join(cfg[k]['default'][k2]['help']) +
                               "\n\n---------------------------------------------------------\n")                    
                parser.add_argument(cfg[k]['default'][k2]['switch'],
                                    dest=k+"_"+k2,
                                    metavar=cfg[k]['default'][k2]['switch_args'],
                                    action='append',
                                    help=helpstr,
                                    default = argparse.SUPPRESS)
        #All others
        else:            
            newkeys =  keys.copy()
            newkeys.append(str(k))            
            if 'defvalue' in cfg[k].keys():                
                keystr = '_'.join(newkeys)
                helpstr = cfg[k]['short_help']
                if longhelp:
                    helpstr = (helpstr +
                               '\n\n' +
                               '\n'.join(cfg[k]['help']) +
                               "\n\n---------------------------------------------------------\n") 
                if cfg[k]['type'][-1] == 'bool': #scalar
                    parser.add_argument(cfg[k]['switch'],
                                        metavar=cfg[k]['switch_args'],
                                        dest=keystr,
                                        action='store_const',
                                        const=['True'],
                                        help=helpstr,
                                        default = argparse.SUPPRESS)
                else:
                    parser.add_argument(cfg[k]['switch'],
                                        metavar=cfg[k]['switch_args'],
                                        dest=keystr,
                                        action='append',
                                        help=helpstr,
                                        default = argparse.SUPPRESS)
            else:
                newkeys.append(str(k))
                add_arg(cfg[k], parser, keys=newkeys) 

###########################
def main():

    #Command line inputs, read once
    cmdlinecfg = cmdline()

    #Control debug level from the command line
    if 'debug' in  cmdlinecfg.keys():
        loglevel = cmdlinecfg['debug']['value'][-1]
    else:
        loglevel = "INFO"
        
    #Create one (or many...) instances of Chip class
    chip = sc.Chip(loglevel=loglevel)
   
    # Reading in config files specified at command line
    if 'cfgfile' in  cmdlinecfg.keys():        
        for cfgfile in cmdlinecfg['cfgfile']['value']:
            chip.readcfg(cfgfile)
        
    #Override cfg with command line args
    chip.mergecfg(cmdlinecfg)

    #Setup target if specified
    if len(chip.cfg['target']['value']) > 0:
        setup_target(chip)
        
    #Resolve as absolute paths (should be a switch)
    #chip.abspath()

    #Checks settings and fills in missing values
    #chip.check()

    #Creating hashes for all sourced files
    chip.hash()

    # Create a 'job hash'.
    job_hash = uuid.uuid4().hex
    chip.status['job_hash'] = job_hash

    #Lock chip configuration
    chip.lock()
    
    all_steps = chip.get('design_flow')
    for stage in all_steps:
        # Run each stage on the remote compute cluster if requested.
        if len(chip.cfg['remote']['value']) > 0:
            remote_run(chip, stage)
        # Run each stage on the local host if no remote server is specified.
        else:
            chip.run(stage)
    
#########################
if __name__ == "__main__":    
    sys.exit(main())
