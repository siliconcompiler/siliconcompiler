# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
from aiohttp import web
import asyncio
import json
import logging as log
import os
import subprocess
import shutil

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
            web.post('/import/{job_hash}', self.handle_import),
            web.get('/check_progress/{job_hash}/{stage}/{jobid}', self.handle_check_progress),
            web.get('/delete_job/{job_hash}', self.handle_delete_job),
        ])
        # TODO: Put zip files in a different directory.
        # And for security reasons, this is not a good public-facing solution.
        # There's no access control on which files can be downloaded.
        # As discussed, a focus on security and access controls will
        # require a more mature server framework based on e.g. apache/nginx/etc.
        self.app.router.add_static('/get_results/', self.cfg['nfsmount']['value'][0])

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

        # Reset 'build' directory in NFS storage.
        build_dir = '%s/%s'%(self.cfg['nfsmount']['value'][0], job_hash)
        cfg['dir']['value'] = [build_dir]
        # Remove 'remote' JSON config value to run locally on compute node.
        cfg['remote']['value'] = []
        # Rename source files in the config dict; the 'import' step already
        # ran and collected the sources into a single 'verilator.sv' file.
        # TODO: Use 'jobid'
        cfg['source']['value'] = ['%s/%s/import/job/verilator.sv'%(self.cfg['nfsmount']['value'][0], job_hash)]
        # Write JSON config to shared compute storage.
        cur_id = cfg['status'][stage]['jobid']['value'][-1]
        subprocess.run(['mkdir', '-p', '%s/configs'%build_dir])
        with open('%s/configs/chip%s.json'%(build_dir, cur_id), 'w') as f:
          f.write(json.dumps(cfg))
        # Symlink the appropriate import directory.
        subprocess.run(['ln', '-s', '%s/import/job'%build_dir, '%s/import/job%s'%(build_dir, str(int(cur_id)+1))])

        # Issue an 'srun' command depending on the given config JSON.
        sc_sources = ''
        for filename in cfg['source']['value']:
          sc_sources += filename + " "
        # (Non-blocking)
        asyncio.create_task(self.remote_sc(job_hash, cfg['design']['value'][0], cfg['source']['value'], build_dir, stage, cur_id))

        # Return a response to the client.
        response_text = "Starting job stage: %s (%s)"%(job_hash, stage)
        return web.Response(text=response_text)

    ####################
    async def handle_import(self, request):
        '''
        API handler for 'import' requests. Accepts a file archive upload,
        which the server extracts into shared compute cluster storage in
        preparation for running a remote job stage.

        TODO: Infer file type from file extension. Currently only supports .zip

        '''

        # Get the job hash value.
        job_hash = request.match_info.get('job_hash', None)
        if not job_hash:
          return web.Response(text="Error: no job hash provided.")
        job_root = '%s/%s'%(self.cfg['nfsmount']['value'][0], job_hash)
        # Receive and write the archive file.
        reader = await request.multipart()
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == 'import':
                # Create the working directory for the given 'job hash' UUID.
                subprocess.run(['mkdir', '-p', job_root])

                # Receive and write the zipped 'import' directory.
                with open('%s/import.zip'%(job_root), 'wb') as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)

        # Un-zip the archive file.
        subprocess.run(['mkdir', '-p', '%s/import/job'%job_root])
        subprocess.run(['unzip', '-o', '%s/import.zip'%(job_root)], cwd='%s/import/job'%job_root)

        # Done.
        return web.Response(text="Successfully imported project %s."%job_hash)

    ####################
    async def handle_delete_job(self, request):
        '''
        API handler for 'delete_job' requests. Delete a job from shared
        cloud compute storage.

        '''

        # Retrieve the job hash to look for.
        job_hash = request.match_info.get('job_hash', None)
        if not job_hash:
            return web.Response(text="Error: no job hash provided.")

        # Determine if the job is running.
        for job in self.sc_jobs:
          if job_hash in job:
            return web.Response(text="Error: job is still running.")

        # Delete job hash directory, only if it exists.
        # TODO: This assumes no malicious input.
        # Again, we will need a more mature server framework to implement
        # good access control and security policies for a public-facing service.
        if not '..' in job_hash:
          build_dir = '%s/%s'%(self.cfg['nfsmount']['value'][0], job_hash)
          if os.path.exists(build_dir):
            #print('Deleting: %s'%build_dir)
            shutil.rmtree(build_dir)
          if os.path.exists('%s.zip'%build_dir):
            #print('Deleting: %s.zip'%build_dir)
            os.remove('%s.zip'%build_dir)

        return web.Response(text="Job deleted.")

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
        jobid = request.match_info.get('jobid', None)
        if not jobid:
          return web.Response(text="Error: no job ID provided.")

        # Determine if the job is running.
        if "%s_%s_%s"%(job_hash, stage, jobid) in self.sc_jobs:
            return web.Response(text="Job is currently running on the cluster.")
        else:
            return web.Response(text="Job has no running steps.")

    ####################
    async def remote_sc(self, job_hash, top_module, sc_sources, build_dir, stage, jobid):
        '''
        Async method to delegate an 'sc' command to a slurm host,
        and send an email notification when the job completes.

        '''

        # Read config JSON, for multi-job configuration.
        jobs_cfg = {}
        with open('%s/configs/chip%s.json'%(build_dir, jobid), 'r') as cfgf:
            jobs_cfg = json.load(cfgf)

        # Mark the job hash as being busy.
        self.sc_jobs["%s_%s_%s"%(job_hash, stage, jobid)] = 'busy'

        # Assemble the 'sc' command. The host must be running slurmctld.
        # TODO: Avoid using a hardcoded $PATH variable for the compute node.
        export_path  = '--export=PATH=/home/ubuntu/OpenROAD-flow-scripts/tools/build/OpenROAD/src'
        export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/TritonRoute'
        export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/yosys/bin'
        export_path += ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin'
        # Send JSON config instead of using subset of flags.
        # TODO: Use slurmpy SDK?
        srun_cmd  = 'srun %s sc /dev/null '%(export_path)
        srun_cmd += '-cfg %s/configs/chip%s.json '%(build_dir, jobid)

        # Create async subprocess shell, and block this thread until it finishes.
        proc = await asyncio.create_subprocess_shell(srun_cmd)
        await proc.wait()

        # (Email notifications can be sent here using SES)

        # Create a single-file archive as part of the 'export' step.
        if stage == 'export':
            subprocess.run(['zip',
                            '-r',
                            '-y',
                            '%s.zip'%job_hash,
                            '%s'%job_hash],
                           cwd=self.cfg['nfsmount']['value'][0])

        # Mark the job hash as being done.
        self.sc_jobs.pop("%s_%s_%s"%(job_hash, stage, jobid))

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
        keystr = str(k)
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

    # Ensure that the default 'value' fields exist.
    for key in def_cfg:
        if (not 'value' in def_cfg[key]) and ('defvalue' in def_cfg[key]):
            def_cfg[key]['value'] = def_cfg[key]['defvalue']

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
