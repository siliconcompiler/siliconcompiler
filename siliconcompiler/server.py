# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from aiohttp import web
import asyncio
import json
import logging as log
import subprocess

from siliconcompiler.cli import server_cmdline

class Server:
    """
    The core class for the siliconcompiler 'gateway' server, which can run
    locally or on a remote host. Its job is to process requests for
    asynchronous siliconcompiler jobs, by using the slurm HPC daemon to
    schedule work on available compute nodes. It can also be configured to
    launch new compute nodes in the cloud, for on-demand jobs.

    """

    ####################
    def __init__(self, loglevel="DEBUG"):
        '''
        Init method for Server object

        '''

        # (Content in future commit)
        pass

    ####################
    def writecfg(self, filename, mode="all"):
        '''
        Writes out the current Server configuration dictionary to a file.

        '''

        # TODO
        pass

def main():
    #Command line inputs and default 'server_schema' config values.
    cmdlinecfg = server_cmdline()

    #Create the Server class instance.
    server = Server(cmdlinecfg)

    #Save the given server configuration in JSON format (not yet implemented)
    server.writecfg("sc_server_setup.json")

    # Start processing incoming requests (implementation in future commit).
    #server.run()

if __name__ == '__main__':
    main()
