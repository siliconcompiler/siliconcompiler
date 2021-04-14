# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import asyncio
import sys
import logging
import argparse
import os
import re
import json
import sys
import uuid
import importlib.resources
from importlib.machinery import SourceFileLoader
from argparse import RawTextHelpFormatter

#Shorten siliconcompiler as sc
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.client import fetch_results
from siliconcompiler.client import remote_run
from siliconcompiler.client import upload_sources_to_cluster

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
    "$ sc 'my_tpu.v' -cfg my_tpu_setup.json                                 ",
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
        # ['asic']['diesize']
        # ['pdk']['rev']
        # ['stdcells'][libname]['lef']
        # ['flow'][stepname]['exe']
        # ['goal'][stepname]['hold_tns']
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
            #TODO: buggy and ugly, fix all of this properly!
            m = re.match('(pdk|asic|fpga)_(.*)', key)
            if m:
                param0 =  m.group(1)
                param2 =  m.group(2)

                if param0 not in cfg:
                    cfg[param0]={}
                if param2 not in cfg[param0]:
                    cfg[param0][param2] = {}
                if 'value' not in cfg[param0][param2]:
                    cfg[param0][param2]['value'] = all_vals                    
                else:
                    cfg[param0][param2]['value'].extend(all_vals)
            else:
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
        #These all have steps
        #dict: 'flow' step 'exe' <str>
        #cli: -flow_exe "step <str>"
        elif k in ('flow'):
            for k2 in cfg[k]['default'].keys():
                helpstr = cfg[k]['default'][k2]['short_help']
                parser.add_argument(cfg[k]['default'][k2]['switch'],
                                    dest=k+"_"+k2,
                                    metavar='',
                                    action='append',
                                    help=helpstr,
                                    default = argparse.SUPPRESS)
        elif k in ('goal', 'real'):
            for k2 in cfg[k]['default']['default'].keys():
                helpstr = cfg[k]['default']['default'][k2]['short_help']
                parser.add_argument(cfg[k]['default']['default'][k2]['switch'],
                                    dest=k+"_"+k2,
                                    metavar='',
                                    action='append',
                                    help=helpstr,
                                    default = argparse.SUPPRESS)
        
        #dict: 'pdk' 'foundry <str>
        #cli: -pdk_foundry "<str>"
        elif k in ('asic', 'fpga', 'pdk'):
             for k2 in cfg[k].keys():
                #Watch out for nesting (like in devicemodel)                
                if 'switch' in cfg[k][k2].keys():
                    helpstr = cfg[k][k2]['short_help']
                    parser.add_argument(cfg[k][k2]['switch'],
                                        dest=k+"_"+k2,
                                        metavar='',
                                        action='append',
                                        help=helpstr,
                                        default = argparse.SUPPRESS)
        #All others
        else:            
            newkeys =  keys.copy()
            newkeys.append(str(k))            
            if 'switch' in cfg[k].keys():                
                keystr = '_'.join(newkeys)
                helpstr = cfg[k]['short_help']
                if cfg[k]['type'][-1] == 'bool': #scalar
                    parser.add_argument(cfg[k]['switch'],
                                        metavar='',
                                        dest=keystr,
                                        action='store_const',
                                        const=['true'],
                                        help=helpstr,
                                        default = argparse.SUPPRESS)
                else:
                    parser.add_argument(cfg[k]['switch'],
                                        metavar='',
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
    
    #Special Command line control for setting up logging
    if 'loglevel' in  cmdlinecfg.keys():
        loglevel = cmdlinecfg['loglevel']['value'][-1]
    else:
        loglevel = "INFO"
        
    # Create a 'job hash' and base Chip class.
    job_hash = uuid.uuid4().hex
    base_chip = siliconcompiler.Chip(loglevel=loglevel)
    base_chip.status['job_hash'] = job_hash

    # Checing for illegal combination
    if ('target' in cmdlinecfg.keys()) & ('cfg' in cmdlinecfg.keys()):
        base_chip.logger.error("Options -target and -cfg are mutually exlusive")
        sys.exit()
    # Reading in config files specified at command line
    elif 'cfg' in  cmdlinecfg.keys():
        for cfgfile in cmdlinecfg['cfg']['value']:
            base_chip.readcfg(cfgfile)
    # Reading in automated target
    else:
        if 'target' in cmdlinecfg.keys():
            base_chip.set('target', cmdlinecfg['target']['value'][0])
        else:
            base_chip.logger.info('No target set, setting to %s','freepdk45')
            base_chip.set('target', 'freepdk45_asic')
        if 'optmode' in cmdlinecfg.keys():
            base_chip.set('optmode', cmdlinecfg['optmode']['value'])
        #Load values based on target name
        base_chip.target()

    # 4. Override cfg with command line args
    base_chip.mergecfg(cmdlinecfg)

    # Create one (or many...) instances of Chip class
    chips = []
    chip_threads = {}
    if 'permutations' in cmdlinecfg.keys():
        perm_path = os.path.abspath(cmdlinecfg['permutations']['value'][-1])
        perm_script = SourceFileLoader('job_perms', perm_path).load_module()
        jobid = 0
        # Create a new Chip object with the same job hash for each permutation.
        for chip_cfg in perm_script.permutations(base_chip.cfg):
            new_chip = siliconcompiler.Chip(loglevel=loglevel)
            # JSON dump/load is a simple way to deep-copy a Python
            # dictionary which does not contain custom classes/objects.
            new_chip.status = json.loads(json.dumps(base_chip.status))
            new_chip.cfg = json.loads(json.dumps(chip_cfg))
            # set incrementing job IDs to avoid overwriting other jobs.
            for step in new_chip.cfg['steps']['value']:
                #new_chip.set('flow', step, 'jobid', str(jobid))
                new_chip.cfg['flow'][step]['jobid']['value'] = [str(jobid)]
            if 'remote' in cmdlinecfg.keys():
                new_chip.set('start', 'syn')
            chips.append(new_chip)
            jobid = jobid + 1
    else:
        # If no permutations script is configured, simply run the design once.
        chips.append(base_chip)

    # Check and lock each permutation.
    for chip in chips:
        #Checks settings and fills in missing values
        chip.check()

        #Creating hashes for all sourced files
        chip.hash()

        #Lock chip configuration
        chip.lock()

    # For remote jobs, run the 'import' stage locally and upload it.
    loop = asyncio.get_event_loop()
    if 'remote' in cmdlinecfg.keys():
        loop.run_until_complete(chips[-1].run(start='import', stop='import'))
        cwd = os.getcwd()
        os.chdir(str(chips[-1].cfg['dir']['value'][-1]) + '/import/job')
        upload_sources_to_cluster(chips[-1])
        os.chdir(cwd)

    # Run each job in parallel (remote) or serially (local).
    # The Chip.run() method is not thread-safe, so no parallel local runs.
    for chip in chips:
        # Running compilation pipeline
        chip_threads[chip] = loop.create_task(chip.run())

    # Wait for threads to complete.
    for chip in chips:
        while not chip_threads[chip].done():
            loop.run_until_complete(asyncio.sleep(1.0))

        # Print Summary
        # TODO: Currently causes errors due to jobid keys.
        #chip.summary()

    # For remote jobs, fetch results.
    if 'remote' in cmdlinecfg.keys():
        fetch_results(chips[-1])
        
#########################
if __name__ == "__main__":    
    sys.exit(main())
