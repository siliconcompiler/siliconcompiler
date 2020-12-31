#!/usr/bin/env python3

# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
import core

###########################
def parse_args(default_args):    

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

    return(cli_args)


###########################
def main():
    
    scc_args            = {}
    scc_args['default'] = scc_init()                    # defines dictionary
    scc_args['env']     = cfg_env(scc_args['default'])  # env variables
    scc_args['cli']     = cfg_cli(scc_args['default'])  # command line args
    scc_args['files']   = {}

    compile(scc_args,"cli")

#########################
if __name__ == "__main__":    
    main()
