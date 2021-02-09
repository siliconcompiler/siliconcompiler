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
    def __init__(self, cmdlinecfg, loglevel="DEBUG"):
        '''
        Init method for Server object

        '''

        # Initialize logger
        self.logger = log.getLogger()
        self.handler = log.StreamHandler()
        self.formatter = log.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(str(loglevel))

        # Use the config that was passed in.
        self.cfg = cmdlinecfg

        # Create a minimal web server to process the 'remote_run' API call.
        self.app = web.Application()
        self.app.add_routes([
            web.post('/remote_run/{job_hash}/{stage}', self.handle_remote_run),
            web.get('/get_results/{job_hash}.zip', self.handle_get_results),
            web.get('/check_progress/{job_hash}/{stage}', self.handle_check_progress),
        ])

        # Start the async server.
        web.run_app(self.app)

    ####################
    async def handle_remote_run(self, request):
        '''
        API handler for 'remote_run' commands. This method delegates
        a 'Chip.run(...)' method to a compute node using slurm.

        '''

        # (Content in future commit)
        pass

    ####################
    async def handle_get_results(self, request):
        '''
        API handler for 'get_results' requests. Currently serves a zip file
        containing logs from each step in the flow. In the future, it will
        probably return a web page containing an SVG render of the floorplan.

        '''

        # TODO: Previously, this zipped the logs from the job and returned that.
        # But the new implementation should copy the entire directory structure
        # from the compute cluster into a local directory.
        pass

    ####################
    async def handle_check_progress(self, request):
        '''
        API handler for the 'check progress' endpoint. Currently,
        It only returns a response containing a 'still running', 'done', or
        'not found' message. In the future, it can respond with up-to-date
        information about the job's progress and intermediary outputs.

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

    # Start processing incoming requests.
    server.run()

if __name__ == '__main__':
    main()
