# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import sys
import os
import re
import json
import argparse
import glob

###########################
def cmdline(default_args):    

    #init of args dictionary to return
    cli_args = {}

    # Argument Parser
    parser = argparse.ArgumentParser(prog='siliconcompiler',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SC)")

    # Source files
    parser.add_argument('sc_source',
                        nargs='+',
                        help=default_args['sc_source']['help'])

    # All other arguments
    for key in default_args.keys():
        if(key!='sc_source'):
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

    return(cli_args)

###########################
def init():

    ###############
    # Compiler file structure
    install_dir = os.path.dirname(os.path.abspath(__file__))
    asic_dir    = install_dir + "/asic/"
    fpga_dir    = install_dir + "/fpga/"
    root_dir    = re.sub("siliconcompiler/siliconcompiler","siliconcompiler",install_dir,1)
    pdklib      = root_dir + "/third_party/pdklib/virtual/nangate45/r1p0/pnr/"

    ###############
    # Single setup dict for all tools

    def_args={}

    ###############
    #Config file
    def_args['sc_cfgfile']             = {}
    def_args['sc_cfgfile']['help']     = "Loads switches from json file"
    def_args['sc_cfgfile']['values']   =  []
    def_args['sc_cfgfile']['switch']   = "-cfgfile"
    
    ###############
    #Technology

    def_args['sc_techfile']             = {}
    def_args['sc_techfile']['help']     = "Place and route tehnology files"
    def_args['sc_techfile']['values']   =  [pdklib + "nangate45.tech.lef"]
    def_args['sc_techfile']['switch']   = "-techfile"

    def_args['sc_minlayer']             = {}
    def_args['sc_minlayer']['help']     = "Minimum routing layer"
    def_args['sc_minlayer']['values']   = ["M2"]
    def_args['sc_minlayer']['switch']   = "-minlayer"

    def_args['sc_maxlayer']             = {}
    def_args['sc_maxlayer']['help']     = "Maximum routing layer"
    def_args['sc_maxlayer']['values']   = ["M7"]
    def_args['sc_maxlayer']['switch']   = "-maxlayer"

    def_args['sc_scenario']             = {}
    def_args['sc_scenario']['help']     = "Process,voltage,temp scenario"
    def_args['sc_scenario']['values']   = ["all timing tt 0.7 25"]
    def_args['sc_scenario']['switch']   = "-scenario"

    ###############
    #Libraries
    iplib       = root_dir + "/third_party/iplib/virtual/nangate45/NangateOpenCellLibrary/r1p0/lib/"
    def_args['sc_lib']                  = {}
    def_args['sc_lib']['help']          = "Standard cell libraries (liberty)"    
    def_args['sc_lib']['values']        = [iplib + "NangateOpenCellLibrary_typical.lib"]
    def_args['sc_lib']['switch']        = "-lib"

    def_args['sc_libheight']            = {}
    def_args['sc_libheight']['help']    = "Height of library (in grids)"
    def_args['sc_libheight']['values']  = [12]
    def_args['sc_libheight']['switch']  = "-libheight"

    def_args['sc_libdriver']            = {}
    def_args['sc_libdriver']['help']    = "Name of default driver cell"
    def_args['sc_libdriver']['values']  = []
    def_args['sc_libdriver']['switch']  = "-libdriver"

    def_args['sc_cell_lists']            = {}
    def_args['sc_cell_lists']['help']    = "Name of default driver cell"
    def_args['sc_cell_lists']['values']  = ["icg", "dontuse", "antenna", "dcap", "filler", "tielo", "tiehi"]
    def_args['sc_cell_lists']['switch']  = "-cell_lists"

    for value in def_args['sc_cell_lists']['values']:
        def_args['sc_' + value]           = {}
        def_args['sc_' + value]['help']   = "List of " + value + " cells"
        def_args['sc_' + value]['values'] = []
        def_args['sc_' + value]['switch'] =  "-" + value
    
    ##################
    # Tool Definitions
   
    def_args['sc_stages']            = {}
    def_args['sc_stages']['help']    = "List of all compilation stages"
    def_args['sc_stages']['values']  = ["import", "syn", "place", "cts", "route", "signoff", "export"]
    def_args['sc_stages']['switch']  = "-stages"
    
    for stage in def_args['sc_stages']['values']:
        #init dict
        def_args['sc_' + stage + '_tool']   = {}
        def_args['sc_' + stage + '_opt']    = {}
        def_args['sc_' + stage + '_dir']    = {}
        def_args['sc_' + stage + '_script'] = {}
        #descriptions
        def_args['sc_' + stage + '_tool']['help']       = "Name of " + stage + " tool"
        def_args['sc_' + stage + '_opt']['help']        = "Options for " + stage + " tool"
        def_args['sc_' + stage + '_dir']['help']        = "Build diretory for " + stage
        def_args['sc_' + stage + '_script']['help']     = "TCL script for " + stage + " tool"
        #command line switches
        def_args['sc_' + stage + '_tool']['switch']     = "-" + stage + "_tool"
        def_args['sc_' + stage + '_opt']['switch']      = "-" + stage + "_opt"
        def_args['sc_' + stage + '_dir']['switch']      = "-" + stage + "_dir"
        def_args['sc_' + stage + '_script']['switch']   = "-" + stage + "_script"        
        #build dir
        def_args['sc_' + stage + '_dir']['values']      = ["build/" + stage]
        if(stage=="import"):
            def_args['sc_import_tool']['values']          = ["verilator"]
            def_args['sc_import_opt']['values']           = ["--lint-only", "--debug"]
            def_args['sc_import_script']['values']        = [" "]
        elif(stage=="syn"):
            def_args['sc_syn_tool']['values']             = ["yosys"]
            def_args['sc_syn_opt']['values']              = ["-c"]
            def_args['sc_syn_script']['values']           = [asic_dir + stage + ".tcl"]
        else:
            def_args['sc_' + stage + '_tool']['values']   = ["openroad"]
            def_args['sc_' + stage + '_opt']['values']    = ["-no_init", "-exit"]
            def_args['sc_' + stage + '_script']['values'] = [asic_dir + stage + ".tcl"]
            
    #################
    #Execution Options
    def_args['sc_jobs']                = {}
    def_args['sc_jobs']['values']      = ["4"]
    def_args['sc_jobs']['switch']      = "-j"
    def_args['sc_jobs']['help']        = "Number of jobs to run simultaneously"

    def_args['sc_effort']              = {}
    def_args['sc_effort']['values']    = ["high"]
    def_args['sc_effort']['switch']    = "-effort"
    def_args['sc_effort']['help']      = "Compilation effort(low,medium,high)"

    def_args['sc_priority']            = {}
    def_args['sc_priority']['values']  = ["speed"]
    def_args['sc_priority']['switch']  = "-priority"
    def_args['sc_priority']['help']    = "Optimization priority(speed,area,power)"

    def_args['sc_start']               = {}
    def_args['sc_start']['values']     = ["import"]
    def_args['sc_start']['switch']     = "-start"
    def_args['sc_start']['help']       = "Stage to start with"

    def_args['sc_stop']                = {}
    def_args['sc_stop']['values']      = ["export"]
    def_args['sc_stop']['switch']      = "-stop"
    def_args['sc_stop']['help']        = "Stage to stop after"        

    def_args['sc_cont']                = {}
    def_args['sc_cont']['values']      = []
    def_args['sc_cont']['switch']      = "-cont"
    def_args['sc_cont']['help']        = "Continue from last completed stage"        

    ###############
    #Design
    def_args['sc_source']              = {}
    def_args['sc_source']['values']    = []
    def_args['sc_source']['switch']    = ""
    def_args['sc_source']['help']      = "Verilog source files, minimum one"

    def_args['sc_topmodule']           = {}
    def_args['sc_topmodule']['values'] = []
    def_args['sc_topmodule']['switch'] = "-topmodule,-m"
    def_args['sc_topmodule']['help']   = "Top module name"

    def_args['sc_clk']                 = {}
    def_args['sc_clk']['values']       = []
    def_args['sc_clk']['switch']       = "-clk"
    def_args['sc_clk']['help']         = "Clock defintions"
    
    def_args['sc_def']                 = {}
    def_args['sc_def']['values']       = []
    def_args['sc_def']['switch']       = "-def"
    def_args['sc_def']['help']         = "Physical floorplan (DEF) file"

    def_args['sc_sdc']                 = {}
    def_args['sc_sdc']['values']       = []
    def_args['sc_sdc']['switch']       = "-sdc"
    def_args['sc_sdc']['help']         = "Constraints (SDC) file"

    def_args['sc_upf']                 = {}
    def_args['sc_upf']['values']       = []
    def_args['sc_upf']['switch']       = "-upf"
    def_args['sc_upf']['help']         = "Unified power format (UPF) file"

    def_args['sc_ydir']                = {}
    def_args['sc_ydir']['values']      = []
    def_args['sc_ydir']['switch']      = "-y"
    def_args['sc_ydir']['help']        = "Directory to search for modules"

    def_args['sc_vlib']                = {}
    def_args['sc_vlib']['values']      = []
    def_args['sc_vlib']['switch']      = "-v"
    def_args['sc_vlib']['help']        = "Verilog library"

    def_args['sc_libext']              = {}
    def_args['sc_libext']['values']    = [".v", ".vh"]
    def_args['sc_libext']['switch']    = "+libext"
    def_args['sc_libext']['help']      = "Extensions for finding modules"

    def_args['sc_idir']                = {}
    def_args['sc_idir']['values']      = []
    def_args['sc_idir']['switch']      = "-I"
    def_args['sc_idir']['help']        = "Directory to search for includes"

    def_args['sc_define']              = {}
    def_args['sc_define']['values']    = []
    def_args['sc_define']['switch']    = "-D"
    def_args['sc_define']['help']      = "Defines for Verilog preprocessor"

    def_args['sc_cmdfile']             = {}
    def_args['sc_cmdfile']['values']   = []
    def_args['sc_cmdfile']['switch']   = "-f"
    def_args['sc_cmdfile']['help']     = "Parse options from file"

    def_args['sc_wall']                = {}
    def_args['sc_wall']['values']      = []
    def_args['sc_wall']['switch']      = "-Wall"
    def_args['sc_wall']['help']        = "Enable all style warnings"

    def_args['sc_wno']                 = {}
    def_args['sc_wno']['values']       = []
    def_args['sc_wno']['switch']       = "-Wno"
    def_args['sc_wno']['help']         = "Disables a warning -Woo-<message>"

    #print(def_args)
    return(def_args)

###########################
def readenv(default_args):    
    env_args = {}
    for key in default_args.keys():
        env_args[key]            = {}
        env_args[key]['values']  = os.getenv(key.upper())
    return(env_args)


###########################
def readjson(default_args,filepath):

    file_args={}
    #Read arguments from file    
    with open(os.path.abspath(jsonfile), "r") as f:
        json_args = args.update(json.load(f))

    #Copy in only values defined in default array
    for key in default_args.keys():
            file_args[key]['values']  = json_args[key]['values']

    return(file_args)

###########################
def mergecfg(all_args, src, dst, opt):
    merge_args = {}
    for key in all_args['default'].keys():
        merge_args[key]           = {}
        merge_args[key]['help']   = all_args['default'][key]['help']
        merge_args[key]['switch'] = all_args['default'][key]['switch']
        if key in all_args[src]:
            if(all_args[src][key]['values'] != None):
                if(opt=="append"):
                    merge_args[key]['values'] = all_args[dst][key]['values'].append(all_args[src][key]['values'])
                else:
                    merge_args[key]['values'] = all_args[src][key]['values']
            #recycle destintation values in case there is no value set in src
            else:
                merge_args[key]['values'] = all_args[dst][key]['values']      
        #This else statement needed in case of empty source dict (eg. no json files supplied)
        else:
            if(key in all_args[dst]):
                merge_args[key]['values'] = all_args[dst][key]['values']
            else:
                print("ERROR: all keys must exist in src or dst dictionary") 
    return(merge_args)
                    
###########################
def printcfg(sc_args,filename=None):
    if(filename==None):
        print(json.dumps(sc_args['merged'], sort_keys=True, indent=4))
    else:
        with open(os.path.abspath(filename), 'w') as f:
            print(json.dumps(sc_args['merged'], sort_keys=True, indent=4), file=f)
    
###########################

def cfgkeys(sc_args):
    return(sorted(sc_args['merged'].keys()))

def getcfg(sc_args,key):
    return (sc_args['merged'][key]['values'])

def setcfg(sc_args,key,values):    
    #TODO: Check that key is in defult!
    sc_args['merged'][key]['values'] = values
    sc_args['merged'][key]['src']    = 'program'
    
###########################
def runstage(sc_args, stage):

    #Moving to working directory
    cwd = os.getcwd()
    output_dir=getcfg(sc_args,'sc_' + stage + '_dir')[0] #scalar!
    os.makedirs(os.path.abspath(output_dir), exist_ok=True)
    os.chdir(os.path.abspath(output_dir))

    #Dump TCL (EDA tcl lacks support for json)
    with open("sc_setup.tcl", 'w') as f:
        print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
        for key in cfgkeys(sc_args):
            values=getcfg(sc_args,key)
            print('set ', key , '  [ list ', end='',file=f)
            for i in values:
                print('\"', i, '\" ', sep='', end='', file=f)
            print(']', file=f)
            
    #Prepare EDA command
    tool    = getcfg(sc_args,'sc_' + stage + '_tool')[0]   #scalar!
    opt     = getcfg(sc_args,'sc_' + stage + '_opt')

    cmd_fields = [tool]
    for value in getcfg(sc_args,'sc_' + stage + '_opt'):
        cmd_fields.append(value)        
    if(stage=="import"):       
        for value in getcfg(sc_args,'sc_ydir'):
            cmd_fields.append('-y ' + os.path.abspath(value))
        for value in getcfg(sc_args,'sc_vlib'):
            cmd_fields.append('-v ' + os.path.abspath(value))
        for value in getcfg(sc_args,'sc_idir'):
            cmd_fields.append('-I ' + os.path.abspath(value))
        for value in getcfg(sc_args,'sc_define'):
            cmd_fields.append('-D ' + value)
        for value in getcfg(sc_args,'sc_source'):
            cmd_fields.append(os.path.abspath(value))
        cmd_fields.append("> verilator.log")    
        script = ""
    else:
        script  = os.path.abspath(getcfg(sc_args,'sc_'+stage+'_script')[0]) #scalar!

    cmd_fields.append(script)           
    cmd   = ' '.join(cmd_fields)

    #execute cmd if current stage is within range of start and stop
    if((getcfg(sc_args,'sc_stages').index(stage) <
       getcfg(sc_args,'sc_stages').index(getcfg(sc_args,'sc_start')[0])) |
       (getcfg(sc_args,'sc_stages').index(stage) >
       getcfg(sc_args,'sc_stages').index(getcfg(sc_args,'sc_stop')[0]))):
        print("SCINFO (", stage, "): Execution skipped due to sc_start/sc_stop setting",sep='')
    else:
        #Run executable
        print(cmd)
        subprocess.run(cmd, shell=True)
        #Post process
        if(stage=="import"):
            #hack: use the --debug feature in verilator to output .vpp files
            #hack: count number of vpp files to find it module==1            
            topmodule = getcfg(sc_args,'sc_topmodule')[0]
            #hack: workaround yosys parser error
            cmd = 'grep -v \`begin_keywords obj_dir/*.vpp >'+topmodule+'.v'
            subprocess.run(cmd, shell=True)
    
    #Return to CWD
    os.chdir(cwd)

###########################
def run(sc_args, mode, filelist=[]):

    if(mode=="cli"):
        # json files appended one by one (priority gets too confusing
        if(sc_args['cli']['sc_cfgfile']['values']!=None):
            filelist=sc_args['cli']['sc_cfgfile']['values']
    for i in range(len(filelist)):
        jsonfile            = 'json'+ i
        sc_args[jsonfile]  = readjson(sc_args['cli']['sc_cfgfile']['values'][i])
        sc_args['files']   = mergecfg(sc_args,'files', jsonfile, "append")
            

    #3. Merging all confifurations (order below defines priority)
    sc_args['merged']  = {}
    sc_args['merged']  = mergecfg(sc_args,'default','merged', "clobber")
    sc_args['merged']  = mergecfg(sc_args,'env',    'merged', "clobber")
    sc_args['merged']  = mergecfg(sc_args,'files',  'merged', "clobber")
    sc_args['merged']  = mergecfg(sc_args,'cli',    'merged', "clobber")

    #4. Print out current config file
    #printcfg(sc_args)

    #5. Run compiler recipe
    runstage(sc_args, "import")
    runstage(sc_args, "syn")
    runstage(sc_args, "place")
    runstage(sc_args, "cts")
    runstage(sc_args, "route"),
    runstage(sc_args, "signoff")
    runstage(sc_args, "export")
