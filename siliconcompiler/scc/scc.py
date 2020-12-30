# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import sys
import argparse
import os
import re
import json

############################
# FUNCTIONS
############################

###########################
def run(scc_args, stage):

    #Moving to working directory
    cwd = os.getcwd()
    output_dir=cfg_get(scc_args,'scc_' + stage + '_dir')[0] #scalar!
    os.makedirs(os.path.abspath(output_dir), exist_ok=True)
    os.chdir(os.path.abspath(output_dir))

    #Dump TCL (EDA tcl lacks support for json)
    with open("scc_setup.tcl", 'w') as f:
        print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
        for key in sorted(scc_args.keys()):
            print('set ', key , scc_args[key], file=f)

    #Prepare EDA command
    tool    = cfg_get(scc_args,'scc_' + stage + '_tool')[0]   #scalar!
    opt     = cfg_get(scc_args,'scc_' + stage + '_opt')

    cmd_fields = [tool]
    for value in cfg_get(scc_args,'scc_' + stage + '_opt'):
        cmd_fields.append(value)        
    if(stage=="import"):       
        for value in cfg_get(scc_args,'scc_ydir'):
            cmd_fields.append('-y ' + os.path.abspath(value))
        for value in cfg_get(scc_args,'scc_vlib'):
            cmd_fields.append('-v ' + os.path.abspath(value))
        for value in cfg_get(scc_args,'scc_idir'):
            cmd_fields.append('-I ' + os.path.abspath(value))
        for value in cfg_get(scc_args,'scc_define'):
            cmd_fields.append('-D ' + value)
        for value in cfg_get(scc_args,'scc_source'):
            cmd_fields.append(os.path.abspath(value))
        script = ""
    else:
        script  = os.path.abspath(cfg_get(scc_args,'scc_' + stage + '_script')[0]) #scalar!

    cmd_fields.append(script)           
    cmd   = ' '.join(cmd_fields)

    #Run executable
    print(cmd)
    #subprocess.run(cmd, shell=True)

    #Post process
    #if(stage=="import"):
    #    subprocess.run('cat obj_dir/*.vpp > output.v', shell=True)
    
    #Return to CWD
    os.chdir(cwd)
    
###########################
def cfg_init():

    ###############
    # Single setup dict for all tools

    def_args={}

    ###############
    #Config file
    def_args['scc_cfgfile']             = {}
    def_args['scc_cfgfile']['help']     = "Loads switches from json file"
    def_args['scc_cfgfile']['values']   =  []
    def_args['scc_cfgfile']['switch']   = "-cfgfile"
    
    ###############
    #Technology
    install_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir    = re.sub("siliconcompiler/siliconcompiler", "siliconcompiler",install_dir,1)
    pdklib      = root_dir + "/third_party/pdklib/virtual/nangate45/r1p0/pnr/"
   
    def_args['scc_techfile']             = {}
    def_args['scc_techfile']['help']     = "Place and route tehnology files"
    def_args['scc_techfile']['values']   =  [pdklib + "nangate45.tech.lef"]
    def_args['scc_techfile']['switch']   = "-techfile"

    def_args['scc_minlayer']             = {}
    def_args['scc_minlayer']['help']     = "Minimum routing layer"
    def_args['scc_minlayer']['values']   = ["M2"]
    def_args['scc_minlayer']['switch']   = "-minlayer"

    def_args['scc_maxlayer']             = {}
    def_args['scc_maxlayer']['help']     = "Maximum routing layer"
    def_args['scc_maxlayer']['values']   = ["M7"]
    def_args['scc_maxlayer']['switch']   = "-maxlayer"

    def_args['scc_scenario']             = {}
    def_args['scc_scenario']['help']     = "Process,voltage,temp scenario"
    def_args['scc_scenario']['values']   = ["all,timing,tt,0.7,25"]
    def_args['scc_scenario']['switch']   = "-scenario"

    ###############
    #Libraries
    iplib       = root_dir + "/third_party/iplib/virtual/nangate45/NangateOpenCellLibrary/r1p0/lib/"
    def_args['scc_lib']                  = {}
    def_args['scc_lib']['help']          = "Standard cell libraries (liberty)"    
    def_args['scc_lib']['values']        = [iplib + "NangateOpenCellLibrary_typical.lib"]
    def_args['scc_lib']['switch']        = "-lib"

    def_args['scc_libheight']            = {}
    def_args['scc_libheight']['help']    = "Height of library (in grids)"
    def_args['scc_libheight']['values']  = [12]
    def_args['scc_libheight']['switch']  = "-libheight"

    def_args['scc_libdriver']            = {}
    def_args['scc_libdriver']['help']    = "Name of default driver cell"
    def_args['scc_libdriver']['values']  = []
    def_args['scc_libdriver']['switch']  = "-libdriver"

    cell_lists = ["icg", "dontuse", "antenna", "dcap", "filler", "tielo", "tiehi"]

    for value in cell_lists:
        def_args['scc_' + value]           = {}
        def_args['scc_' + value]['help']   = "List of " + value + " cells"
        def_args['scc_' + value]['values'] = []
        def_args['scc_' + value]['switch'] =  "-" + value
    
    ##################
    # Tool Definitions
    
    all_stages = ["import", "syn", "place", "cts", "route", "signoff", "export"]

    for stage in all_stages:
        #init dict
        def_args['scc_' + stage + '_tool']   = {}
        def_args['scc_' + stage + '_opt']    = {}
        def_args['scc_' + stage + '_dir']    = {}
        def_args['scc_' + stage + '_script'] = {}
        #descriptions
        def_args['scc_' + stage + '_tool']['help']       = "Name of " + stage + " tool"
        def_args['scc_' + stage + '_opt']['help']        = "Options for " + stage + " tool"
        def_args['scc_' + stage + '_dir']['help']        = "Build diretory for " + stage
        def_args['scc_' + stage + '_script']['help']     = "TCL script for " + stage + " tool"
        #command line switches
        def_args['scc_' + stage + '_tool']['switch']     = "-" + stage + "_tool"
        def_args['scc_' + stage + '_opt']['switch']      = "-" + stage + "_opt"
        def_args['scc_' + stage + '_dir']['switch']      = "-" + stage + "_dir"
        def_args['scc_' + stage + '_script']['switch']   = "-" + stage + "_script"        
        #build dir
        def_args['scc_' + stage + '_dir']['values']      = ["build/" + stage]
        if(stage=="import"):
            def_args['scc_import_tool']['values']          = ["verilator"]
            def_args['scc_import_opt']['values']           = ["--lint-only", "--debug"]
            def_args['scc_import_script']['values']        = [" "]
        elif(stage=="syn"):
            def_args['scc_syn_tool']['values']             = ["yosys"]
            def_args['scc_syn_opt']['values']              = ["-c"]
            def_args['scc_syn_script']['values']           = [install_dir + "/asic/" + stage + ".tcl"]
        else:
            def_args['scc_' + stage + '_tool']['values']   = ["openroad"]
            def_args['scc_' + stage + '_opt']['values']    = ["-no_init", "-exit"]
            def_args['scc_' + stage + '_script']['values'] = [install_dir + "/asic/" + stage + ".tcl"]
            
    #################
    #Execution Options
    def_args['scc_jobs']                = {}
    def_args['scc_jobs']['values']      = ["4"]
    def_args['scc_jobs']['switch']      = "-j"
    def_args['scc_jobs']['help']        = "Number of jobs to run simultaneously"

    def_args['scc_effort']              = {}
    def_args['scc_effort']['values']    = ["high"]
    def_args['scc_effort']['switch']    = "-effort"
    def_args['scc_effort']['help']      = "Compilation effort(low,medium,high)"

    def_args['scc_priority']            = {}
    def_args['scc_priority']['values']  = ["speed"]
    def_args['scc_priority']['switch']  = "-priority"
    def_args['scc_priority']['help']    = "Optimization priority(speed,area,power)"

    def_args['scc_start']               = {}
    def_args['scc_start']['values']     = ["import"]
    def_args['scc_start']['switch']     = "-start"
    def_args['scc_start']['help']       = "Stage to start with"

    def_args['scc_stop']                = {}
    def_args['scc_stop']['values']      = ["export"]
    def_args['scc_stop']['switch']      = "-stop"
    def_args['scc_stop']['help']        = "Stage to stop after"        

    ###############
    #Design
    def_args['scc_source']              = {}
    def_args['scc_source']['values']    = []
    def_args['scc_source']['switch']    = ""
    def_args['scc_source']['help']      = "Verilog source files, minimum one"

    def_args['scc_topmodule']           = {}
    def_args['scc_topmodule']['values'] = []
    def_args['scc_topmodule']['switch'] = "-topmodule"
    def_args['scc_topmodule']['help']   = "Top module name"

    def_args['scc_clk']                 = {}
    def_args['scc_clk']['values']       = []
    def_args['scc_clk']['switch']       = "-clk"
    def_args['scc_clk']['help']         = "Clock defintions"
    
    def_args['scc_def']                 = {}
    def_args['scc_def']['values']       = []
    def_args['scc_def']['switch']       = "-def"
    def_args['scc_def']['help']         = "Physical floorplan (DEF) file"

    def_args['scc_sdc']                 = {}
    def_args['scc_sdc']['values']       = []
    def_args['scc_sdc']['switch']       = "-sdc"
    def_args['scc_sdc']['help']         = "Constraints (SDC) file"

    def_args['scc_upf']                 = {}
    def_args['scc_upf']['values']       = []
    def_args['scc_upf']['switch']       = "-upf"
    def_args['scc_upf']['help']         = "Unified power format (UPF) file"

    def_args['scc_ydir']                = {}
    def_args['scc_ydir']['values']      = []
    def_args['scc_ydir']['switch']      = "-y"
    def_args['scc_ydir']['help']        = "Directory to search for modules"

    def_args['scc_vlib']                = {}
    def_args['scc_vlib']['values']      = []
    def_args['scc_vlib']['switch']      = "-v"
    def_args['scc_vlib']['help']        = "Verilog library"

    def_args['scc_libext']              = {}
    def_args['scc_libext']['values']    = [".v", ".vh"]
    def_args['scc_libext']['switch']    = "+libext"
    def_args['scc_libext']['help']      = "Extensions for finding modules"

    def_args['scc_idir']                = {}
    def_args['scc_idir']['values']      = []
    def_args['scc_idir']['switch']      = "-I"
    def_args['scc_idir']['help']        = "Directory to search for includes"

    def_args['scc_define']              = {}
    def_args['scc_define']['values']    = []
    def_args['scc_define']['switch']    = "-D"
    def_args['scc_define']['help']      = "Defines for Verilog preprocessor"

    def_args['scc_cmdfile']             = {}
    def_args['scc_cmdfile']['values']   = []
    def_args['scc_cmdfile']['switch']   = "-f"
    def_args['scc_cmdfile']['help']     = "Parse options from file"

    def_args['scc_wall']                = {}
    def_args['scc_wall']['values']      = []
    def_args['scc_wall']['switch']      = "-Wall"
    def_args['scc_wall']['help']        = "Enable all style warnings"

    def_args['scc_wno']                 = {}
    def_args['scc_wno']['values']       = []
    def_args['scc_wno']['switch']       = "-Wno"
    def_args['scc_wno']['help']         = "Disables a warning -Woo-<message>"

    #print(def_args)
    return(def_args)

###########################
def cfg_env(default_args):    
    env_args = {}
    for key in default_args.keys():
        env_args[key]            = {}
        env_args[key]['values']  = os.getenv(key.upper())
    #print(env_args)	
    return(env_args)


###########################
def cfg_cli(default_args):    

    #init of args dictionary to return
    cli_args = {}

    # Argument Parser
    parser = argparse.ArgumentParser(prog='scc',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SCC)")

    # Source files
    parser.add_argument('scc_source',
                        nargs='+',
                        help=default_args['scc_source']['help'])

    # All other arguments
    for key in default_args.keys():
        print(key)
        if(key!='scc_source'):
            parser.add_argument(default_args[key]['switch'],
                                dest=key,
                                action='append',
                                help=default_args[key]['help'])
        
    # Parse the cli arguments
    args=parser.parse_args()

    # Copy the arguments into dictionary format
    for arg in vars(args):
        cli_args[arg]           = {}
        
        cli_args[arg]['values'] = getattr(args, arg)

    print("CLI", args)	
    return(cli_args)

###########################
def cfg_json(default_args,filepath):

    file_args={}
    #Read arguments from file    
    with open(os.path.abspath(jsonfile), "r") as f:
        json_args = args.update(json.load(f))

    #Copy in only values defined in default array
    for key in default_args.keys():
            file_args[key]['values']  = json_args[key]['values']

    print('FILE', filepath, file_args)
    return(file_args)

###########################
def cfg_merge(all_args, src, dst, opt):
    merge_args = {}
    for key in all_args['default'].keys():
        merge_args[key]           = {}
        merge_args[key]['values'] = all_args['default'][key]['values']
        merge_args[key]['help']   = all_args['default'][key]['help']
        merge_args[key]['src']    = "default"
        print(key, src)
        if key in all_args[src]:
            if(all_args[src][key]['values'] != None):
                if(opt=="append"):
                    merge_args[key]['values'] = all_args[dst][key]['values'].append(all_args[src][key]['values'])
                else:
                    merge_args[key]['values'] = all_args[src][key]['values']
        
    print(merge_args)
    return(merge_args)

###########################
def cfg_print(scc_args):
    print(json.dumps(scc_args, sort_keys=True, indent=4))

###########################
def cfg_get(scc_args,key):
    return (scc_args['merged'][key]['values'])

###########################
def cfg_set(scc_args,key,values):    
    scc_args['merged'][key]['values'] = values
    scc_args['merged'][key]['src']    = 'program'
    
############################
# COMMAND LINE SCRIPT
############################
if __name__ == "__main__":

    #1. Reading args (in many ways...)
    scc_args            = {}
    scc_args['default'] = cfg_init()                        # defines dictionary
    scc_args['env']     = cfg_env(scc_args['default'])  # env variables
    scc_args['cli']     = cfg_cli(scc_args['default'])  # command line args

    #2. Reading in all json config files (append operation)
    scc_args['files'] = {}
    if(scc_args['cli']['scc_cfgfile']['values']!=None):
        for i in range(len(scc_args['cli']['scc_cfgfile']['values'])):
            jsonfile            = 'json'+ i
            scc_args[jsonfile]  = cfg_json(scc_args['cli']['scc_cfgfile']['values'][i])
            scc_args['files']   = cfg_merge(scc_args,'files', jsonfile, "append")

    #3. Merging all confifurations (order below defines priority)
    scc_args['merged']  = {}
    scc_args['merged']  = cfg_merge(scc_args,'default','merged', "clobber")
    scc_args['merged']  = cfg_merge(scc_args,'env',    'merged', "clobber")
    scc_args['merged']  = cfg_merge(scc_args,'files',  'merged', "clobber")
    scc_args['merged']  = cfg_merge(scc_args,'cli',    'merged', "clobber")

    #3. Print out current config file
    cfg_print(scc_args)

    #4. Run compiler
    run(scc_args, "import")
    run(scc_args, "syn")
    run(scc_args, "place")
    run(scc_args, "cts")
    run(scc_args, "route"),
    run(scc_args, "signoff")
    run(scc_args, "export")


