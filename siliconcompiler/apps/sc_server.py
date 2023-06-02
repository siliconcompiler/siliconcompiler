# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse

from siliconcompiler.remote.schema import server_schema
from siliconcompiler.remote.server import Server


###############################################
# Helper method to parse sc-server command-line args.
###############################################
def server_cmdline():
    '''
    Command-line parsing for sc-server variables.
    TODO: It may be a good idea to merge with 'cmdline()' to reduce code duplication.
    '''

    progname = "sc-server"
    description = """
    Silicon Compiler Collection Remote Job Server (sc-server)
    """

    def_cfg = server_schema()

    # Argument Parser
    parser = argparse.ArgumentParser(prog=progname,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prefix_chars='-+',
                                     description=description)

    # Add supported schema arguments to the parser.
    for k, _ in sorted(def_cfg.items()):
        keystr = str(k)
        helpstr = def_cfg[k]['short_help'] + \
            '\n\n' + \
            '\n'.join(def_cfg[k]['help'])
        if def_cfg[k]['type'][-1] == 'bool':  # scalar
            parser.add_argument(def_cfg[k]['switch'],
                                metavar=def_cfg[k]['switch_args'],
                                dest=keystr,
                                action='store_const',
                                const=['True'],
                                help=helpstr,
                                default=argparse.SUPPRESS)
        else:
            parser.add_argument(def_cfg[k]['switch'],
                                metavar=def_cfg[k]['switch_args'],
                                dest=keystr,
                                action='append',
                                help=helpstr,
                                default=argparse.SUPPRESS)

    # Parsing args and converting to dict
    cmdargs = vars(parser.parse_args())

    # Generate nested cfg dictionary.
    for key, all_vals in cmdargs.items():
        switch = key.split('_')
        param = switch[0]
        if len(switch) > 1:
            param = param + "_" + switch[1]

        if param not in def_cfg:
            def_cfg[param] = {}

        # (Omit checks for stdcell, maro, etc; server args are simple.)

        if 'value' not in def_cfg[param]:
            def_cfg[param] = {}
            def_cfg[param]['value'] = all_vals
        else:
            def_cfg[param]['value'].extend(all_vals)

    # Ensure that the default 'value' fields exist.
    for key in def_cfg:
        if ('value' not in def_cfg[key]) and ('defvalue' in def_cfg[key]):
            def_cfg[key]['value'] = def_cfg[key]['defvalue']

    return def_cfg


###############################################
# Main method to run the sc-server application.
###############################################
def main():
    # Command line inputs and default 'server_schema' config values.
    cmdlinecfg = server_cmdline()

    # Create the Server class instance.
    Server(cmdlinecfg)


if __name__ == '__main__':
    main()
