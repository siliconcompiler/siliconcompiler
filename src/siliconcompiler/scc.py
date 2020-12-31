# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

def compile(mode,filelist=[]):

    ###########################################################################
    #1. Reading args (in many ways...)
    scc_args            = {}
    scc_args['default'] = cfg_init()                    # defines dictionary
    scc_args['env']     = cfg_env(scc_args['default'])  # env variables
    scc_args['files'] = {}
    if(mode=="cli"):
        scc_args['cli']     = cfg_cli(scc_args['default'])  # command line args
        # json files appended one by one (priority gets too confusing
        if(scc_args['cli']['scc_cfgfile']['values']!=None):
            filelist=scc_args['cli']['scc_cfgfile']['values']
    for i in range(len(filelist)):
        jsonfile            = 'json'+ i
        scc_args[jsonfile]  = cfg_json(scc_args['cli']['scc_cfgfile']['values'][i])
        scc_args['files']   = cfg_merge(scc_args,'files', jsonfile, "append")
            
    ###############################################################################
    #2. Merging all confifurations (order below defines priority)

    scc_args['merged']  = {}
    scc_args['merged']  = cfg_merge(scc_args,'default','merged', "clobber")
    scc_args['merged']  = cfg_merge(scc_args,'env',    'merged', "clobber")
    scc_args['merged']  = cfg_merge(scc_args,'files',  'merged', "clobber")
    scc_args['merged']  = cfg_merge(scc_args,'cli',    'merged', "clobber")

    #############################################################################
    #3. Print out current config file
    cfg_print(scc_args,"build/setup.json")

    #############################################################################
    #4. Run compiler

    run(scc_args, "import")
    run(scc_args, "syn")
    run(scc_args, "place")
    run(scc_args, "cts")
    run(scc_args, "route"),
    run(scc_args, "signoff")
    run(scc_args, "export")

#########################
if __name__ == "__main__":    
    compile("cli")
