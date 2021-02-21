# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
from aiohttp import web
import asyncio
import json
import logging as log
import os
import subprocess

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

        # Set up a dictionary to track running jobs.
        self.sc_jobs = {}

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

        # Retrieve JSON config into a dictionary.
        cfg = await request.json()
        job_hash = request.match_info.get('job_hash', None)
        if not job_hash:
          return web.Response(text="Error: no job hash provided.")
        stage = request.match_info.get('stage', None)
        if not stage:
          return web.Response(text="Error: no stage provided.")

        # Write JSON config to shared compute storage.
        build_dir = '%s/%s'%(cfg['nfsmount']['value'][0], job_hash)
        with open('%s/chip.json'%build_dir, 'w') as f:
          f.write(json.dumps(cfg))

        # Issue an 'srun' command depending on the given config JSON.
        sc_sources = ''
        for filename in cfg['source']['value']:
          sc_sources += filename + " "
        # (Non-blocking)
        asyncio.create_task(self.remote_sc(job_hash, cfg['design']['value'][0], cfg['source']['value'], build_dir, stage))

        # Return a response to the client.
        response_text = "Starting step: %s"%stage
        return web.Response(text=response_text)

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

        # Retrieve the job hash to look for.
        job_hash = request.match_info.get('job_hash', None)
        if not job_hash:
            return web.Response(text="Error: no job hash provided.")
        stage = request.match_info.get('stage', None)
        if not stage:
          return web.Response(text="Error: no stage provided.")

        # Determine if the job is running.
        if "%s_%s"%(job_hash, stage) in self.sc_jobs:
            return web.Response(text="Job is currently running on the cluster.")
        else:
            return web.Response(text="Job has no running steps.")

    ####################
    #async def remote_sc(self, job_hash, chip_cfg, stage):
    async def remote_sc(self, job_hash, top_module, sc_sources, build_dir, stage):
        '''
        Async method to delegate an 'sc' command to a slurm host,
        and send an email notification when the job completes.

        '''

        # Mark the job hash as being busy.
        self.sc_jobs["%s_%s"%(job_hash, stage)] = 'busy'

        # Assemble the 'sc' command. The host must be running slurmctld.
        # TODO: Avoid using a hardcoded $PATH variable for the compute node.
        export_path  = '--export=PATH=/home/ubuntu/OpenROAD-flow-scripts/tools/build/OpenROAD/src'
        export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/TritonRoute'
        export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/yosys/bin'
        export_path += ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin'
        # Send JSON config instead of using subset of flags.
        # TODO: Use slurmpy SDK?
        #srun_cmd = 'srun %s sc - %s'%(export_path, chip_cfg)
        srun_cmd = 'srun %s sc'%export_path
        for src in sc_sources:
            srun_cmd += ' ' + src
        srun_cmd += ' -target nangate45 -design %s'%(top_module)
        srun_cmd += ' -build %s'%build_dir
        srun_cmd += ' -start %s -stop %s'%(stage, stage)

        # Create async subprocess shell, and block this thread until it finishes.
        proc = await asyncio.create_subprocess_shell(srun_cmd)
        await proc.wait()

        # (Email notifications can be sent here using SES)

        # Mark the job hash as being done.
        self.sc_jobs.pop("%s_%s"%(job_hash, stage))

    ####################
    def writecfg(self, filename, mode="all"):
        '''
        Writes out the current Server configuration dictionary to a file.

        '''

        # TODO
        pass

###############################################
# Configuration schema for `sc-server`
###############################################

def server_schema():
    '''Method for defining Server configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    cfg = {}

    cfg['port'] = {
        'short_help': 'Port number to run the server on.',
        'switch': '-port',
        'switch_args': '<num>',
        'type': ['int'],
        'defvalue': ['8080'],
        'help' : ["TBD"]
    }

    cfg['nfsuser'] = {
        'short_help': 'Username on remote storage host.',
        'switch': '-nfs_user',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue': ['ubuntu'],
        'help' : ["TBD"]
    }

    cfg['nfshost'] = {
        'short_help': 'Hostname or IP address for shared storage.',
        'switch': '-nfs_host',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue' : [],
        'help' : ["TBD"]
    }

    cfg['nfsmount'] = {
        'short_help': 'Directory of mounted shared NFS storage.',
        'switch': '-nfs_mount',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue' : ['/nfs/sc_compute'],
        'help' : ["TBD"]
    }

    cfg['nfskey'] = {
        'short_help': 'Key-file used for remote connection.',
        'switch': '-nfs_key',
        'switch_args': '<file>',
        'type': ['file'],
        'defvalue' : [],
        'help' : ["TBD"]
    }

    return cfg

###############################################
# Helper method to parse sc-server command-line args.
###############################################

def server_cmdline():
    '''
    Command-line parsing for sc-server variables.
    TODO: It may be a good idea to merge with 'cmdline()' to reduce code duplication.

    '''

    def_cfg = server_schema()

    os.environ["COLUMNS"] = '100'

    #Argument Parser
    parser = argparse.ArgumentParser(prog='sc-server',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection Remote Job Server (sc-server)")

    # Add supported schema arguments to the parser.
    for k,v in sorted(def_cfg.items()):
        keystr = '_'.join(str(k))
        helpstr = (def_cfg[k]['short_help'] +
                   '\n\n' +
                   '\n'.join(def_cfg[k]['help']) +
                   '\n\n---------------------------------------------------------\n')
        if def_cfg[k]['type'][-1] == 'bool': #scalar
            parser.add_argument(def_cfg[k]['switch'],
                                metavar=def_cfg[k]['switch_args'],
                                dest=keystr,
                                action='store_const',
                                const=['True'],
                                help=helpstr,
                                default = argparse.SUPPRESS)
        else:
            parser.add_argument(def_cfg[k]['switch'],
                                metavar=def_cfg[k]['switch_args'],
                                dest=keystr,
                                action='append',
                                help=helpstr,
                                default = argparse.SUPPRESS)

    #Parsing args and converting to dict
    cmdargs = vars(parser.parse_args())

    # Generate nested cfg dictionary.
    for key,all_vals in cmdargs.items():
        switch = key.split('_')
        param = switch[0]
        if len(switch) > 1 :
            param = param + "_" + switch[1]

        if param not in def_cfg:
            def_cfg[param] = {}

        #(Omit checks for stdcell, maro, etc; server args are simple.)

        if 'value' not in def_cfg[param]:
            def_cfg[param] = {}
            def_cfg[param]['value'] = all_vals
        else:
            def_cfg[param]['value'].extend(all_vals)

    return def_cfg

###############################################
# Main method to run the sc-server application.
###############################################

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
