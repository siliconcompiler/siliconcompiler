# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from aiohttp import web
import asyncio
import base64
import json
import logging as log
import os
import re
import shutil
import uuid
import tempfile
import tarfile

from siliconcompiler import Chip
from siliconcompiler import Schema
from siliconcompiler import utils

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
        self.logger = log.getLogger(uuid.uuid4().hex)
        self.handler = log.StreamHandler()
        self.formatter = log.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(loglevel)

        # Use the config that was passed in.
        self.cfg = cmdlinecfg
        # Ensure that NFS mounting path is absolute.
        self.cfg['nfsmount']['value'] = [os.path.abspath(nfs_path) for nfs_path in self.cfg['nfsmount']['value']]

        # Set up a dictionary to track running jobs.
        self.sc_jobs = {}

        # If authentication is enabled, try connecting to the SQLite3 database.
        # (An empty one will be created if it does not exist.)

        # If authentication is enabled, load [username : password/key] mappings.
        # Remember, this development server is intended to be a minimal
        # demonstration of the API, and should only be used for testing purposes.
        # You should NEVER store plaintext passwords in a production
        # server implementation.
        if self.cfg['auth']['value'][-1]:
            self.user_keys = {}
            json_path = os.path.join(self.nfs_mount, 'users.json')
            try:
                with open(json_path, 'r') as users_file:
                    users_json = json.loads(users_file.read())
                for mapping in users_json['users']:
                    username = mapping['username']
                    self.user_keys[username] = {
                        'password': mapping['password']
                    }
                    if 'compute_time' in mapping:
                        self.user_keys[username]['compute_time'] = mapping['compute_time']
                    if 'bandwidth' in mapping:
                        self.user_keys[username]['bandwidth'] = mapping['bandwidth']
            except Exception:
                self.logger.warning("Could not find well-formatted 'users.json' "\
                                    "file in the server's working directory. "\
                                    "(User : Key) mappings were not imported.")

        # Create a minimal web server to process the 'remote_run' API call.
        self.app = web.Application()
        self.app.add_routes([
            web.post('/remote_run/', self.handle_remote_run),
            web.post('/check_progress/', self.handle_check_progress),
            web.post('/check_user/', self.handle_check_user),
            web.post('/delete_job/', self.handle_delete_job),
            web.post('/get_results/{job_hash}.tar.gz', self.handle_get_results),
        ])
        # TODO: Put zip files in a different directory.
        # For security reasons, this is not a good public-facing solution.
        # There's no access control on which files can be downloaded.
        # But this is an example server which only implements a minimal API.
        self.app.router.add_static('/get_results/', self.nfs_mount)

        # Start the async server.
        web.run_app(self.app, port = int(self.cfg['port']['value'][-1]))

    ####################
    async def handle_remote_run(self, request):
        '''
        API handler for 'remote_run' commands. This method delegates
        a 'Chip.run(...)' method to a compute node using slurm.
        '''

        # Temporary file path to store streamed data.
        tmp_file = os.path.join(self.nfs_mount, uuid.uuid4().hex)

        # Set up a multipart reader to read in the large file, and param data.
        reader = await request.multipart()
        while True:
            # Get the next part; if it doesn't exist, we're done.
            part = await reader.next()
            if part is None:
                break

            # Save the initial 'import' step archive. Note: production server
            # implementations may want to encrypt data before storing it on disk.
            if part.name == 'import':
                with open(tmp_file, 'wb') as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)

            # Retrieve JSON request parameters.
            elif part.name == 'params':
                # Get the job parameters.
                params = await part.json()
                job_params = params['params']
                cfg = params['chip_cfg']

        # Get the job hash value, and verify it is a 32-char hex string.
        if not 'job_hash' in job_params:
            return web.Response(text="Error: no job hash provided.")
        job_hash = job_params['job_hash']
        if not re.match("^[0-9A-Za-z]{32}$", job_hash):
            return web.Response(text="Error: invalid job hash.")
        # Check for authentication parameters.
        use_auth = False
        if ('username' in job_params) or ('key' in job_params):
            if self.cfg['auth']['value'][-1]:
                if ('username' in job_params) and ('key' in job_params):
                    username = job_params['username']
                    key = job_params['key']
                    if not username in self.user_keys.keys():
                        return web.Response(text="Error: invalid username provided.", status=404)
                    # Authenticate the user.
                    if self.auth_password(username, key):
                        use_auth = True
                    else:
                        return web.Response(text="Authentication error.", status=403)
                else:
                    return web.Response(text="Error: some authentication parameters are missing.", status=400)
            else:
                return web.Response(text="Error: authentication parameters were passed in, but this server does not support that feature.", status=500)

        # Create a dummy Chip object to make schema traversal easier.
        # TODO: if this is a dummy Chip we should be able to use Schema class,
        # but looks like it relies on chip.status.
        # start with a dummy name, as this will be overwritten
        chip = Chip('server')
        # Add provided schema
        chip.schema = Schema(cfg=cfg)

        # Fetch some common values.
        design = chip.get('design')
        job_name = chip.get('option', 'jobname')
        job_nameid = f'{job_name}'
        chip.status['jobhash'] = job_hash

        # Ensure that the job's root directory exists.
        job_root = os.path.join(self.nfs_mount, job_hash)
        job_dir  = os.path.join(job_root, design, job_name)
        os.makedirs(job_dir, exist_ok=True)

        # Move the uploaded archive and un-zip it.
        # (Contents will be encrypted for authenticated jobs)
        with tarfile.open(tmp_file, "r:gz") as tar:
            tar.extractall(path=job_dir)

        # Delete the temporary file if it still exists.
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        # Reset 'build' directory in NFS storage.
        build_dir = os.path.join(self.nfs_mount, job_hash)
        jobs_dir = os.path.join(build_dir, chip.get('design'))
        job_nameid = f"{chip.get('option', 'jobname')}"

        # Create the working directory for the given 'job hash' if necessary.
        os.makedirs(jobs_dir, exist_ok=True)
        chip.set('option', 'builddir', build_dir, clobber=True)
        # Link to the 'import' directory if necessary.
        os.makedirs(os.path.join(jobs_dir, job_nameid), exist_ok=True)

        # Remove 'remote' JSON config value to run locally on compute node.
        chip.set('option', 'remote', False, clobber=True)
        chip.set('option', 'credentials', '', clobber=True)

        # Write JSON config to shared compute storage.
        os.makedirs(os.path.join(build_dir, 'configs'), exist_ok=True)

        # Run the job with the configured clustering option. (Non-blocking)
        if use_auth:
            asyncio.ensure_future(self.remote_sc(chip,
                                                 username))
        else:
            asyncio.ensure_future(self.remote_sc(chip, None))

        # Return a response to the client.
        response_text = f"Starting job: {job_hash}"
        return web.Response(text=response_text)

    ####################
    async def handle_get_results(self, request):
        '''
        API handler to redirect 'get_results' POST calls.
        '''

        # Retrieve the job hash.
        job_hash = request.match_info.get('job_hash', None)
        if not job_hash:
            return web.Response(text="Error: no job hash provided.")
        params = await request.json()

        # Check whether to use authentication.
        use_auth = False
        if ('username' in params) or ('key' in params):
            if self.cfg['auth']['value'][-1]:
                if ('username' in params) and ('key' in params):
                    username = params['username']
                    key = params['key']
                    if not username in self.user_keys.keys():
                        return web.Response(text="Error: invalid username provided.", status=404)
                    # Authenticate the user.
                    if self.auth_password(username, key):
                        use_auth = True
                    else:
                        return web.Response(text="Authentication error.", status=403)
                else:
                    return web.Response(text="Error: some authentication parameters are missing.", status=400)
            else:
                return web.Response(text="Error: authentication parameters were passed in, but this server does not support that feature.", status=500)

        resp = web.StreamResponse(
            status = 200,
            reason = 'OK',
            headers = {
                'Content-Type': 'application/x-tar',
                'Content-Disposition': f'attachment; filename="{job_hash}.tar.gz"'
            },
        )
        await resp.prepare(request)

        zipfn = os.path.join(self.nfs_mount, f'{job_hash}.tar.gz')
        with open(zipfn, 'rb') as zipf:
            await resp.write(zipf.read())

        await resp.write_eof()
        return resp

    ####################
    async def handle_delete_job(self, request):
        '''
        API handler for 'delete_job' requests. Delete a job from shared
        cloud compute storage.

        '''

        # Retrieve the JSON parameters.
        params = await request.json()
        if not 'job_hash' in params:
            return web.Response(text="Error: no job hash provided.")
        job_hash = params['job_hash']

        # Check for authentication parameters.
        use_auth = False
        if ('username' in params) or ('key' in params):
            if self.cfg['auth']['value'][-1]:
                if ('username' in params) and ('key' in params):
                    username = params['username']
                    key = params['key']
                    if not username in self.user_keys.keys():
                        return web.Response(text="Error: invalid username provided.", status=404)
                    # Authenticate the user.
                    if self.auth_password(username, key):
                        use_auth = True
                    else:
                        return web.Response(text="Authentication error.", status=403)
                else:
                    return web.Response(text="Error: some authentication parameters are missing.", status=400)
            else:
                return web.Response(text="Error: authentication parameters were passed in, but this server does not support that feature.", status=500)

        # Determine if the job is running.
        for job in self.sc_jobs:
          if job_hash in job:
            return web.Response(text="Error: job is still running.")

        # Delete job hash directory, only if it exists.
        # TODO: This assumes no malicious input.
        # Again, we will need a more mature server framework to implement
        # good access control and security policies for a public-facing service.
        if not '..' in job_hash:
            build_dir = os.path.join(self.nfs_mount, job_hash)
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)

            tar_file = f'{build_dir}.tar.gz'
            if os.path.exists(tar_file):
                os.remove(tar_file)

        return web.Response(text="Job deleted.")

    ####################
    async def handle_check_progress(self, request):
        '''
        API handler for the 'check progress' endpoint. Currently,
        It only returns a response containing a 'still running', 'done', or
        'not found' message. In the future, it can respond with up-to-date
        information about the job's progress and intermediary outputs.
        '''

        # Retrieve the JSON parameters.
        params = await request.json()
        if not 'job_hash' in params:
            return web.Response(text="Error: no job hash provided.")
        job_hash = params['job_hash']
        if not 'job_id' in params:
            return web.Response(text="Error: no job ID provided.")
        jobid = params['job_id']
        username = ''
        if 'username' in params:
            username = params['username']

        # Check for authentication parameters.
        use_auth = False
        if ('username' in params) or ('key' in params):
            if self.cfg['auth']['value'][-1]:
                if ('username' in params) and ('key' in params):
                    username = params['username']
                    key = params['key']
                    if not username in self.user_keys.keys():
                        return web.Response(text="Error: invalid username provided.", status=404)
                    # Authenticate the user.
                    if self.auth_password(username, key):
                        use_auth = True
                    else:
                        return web.Response(text="Authentication error.", status=403)
                else:
                    return web.Response(text="Error: some authentication parameters are missing.", status=400)
            else:
                return web.Response(text="Error: authentication parameters were passed in, but this server does not support that feature.", status=500)

        # Determine if the job is running.
        if "%s%s_%s"%(username, job_hash, jobid) in self.sc_jobs:
            return web.Response(text="Job is currently running on the cluster.")
        else:
            return web.Response(text="Job has no running steps.")

    ####################
    async def handle_check_user(self, request):
        '''
        API handler for the 'check user' endpoint.
        '''

        # Retrieve the JSON parameters.
        params = await request.json()
        username = ''
        if 'username' in params:
            username = params['username']

        # Check for authentication parameters.
        use_auth = False
        if ('username' in params) or ('key' in params):
            if self.cfg['auth']['value'][-1]:
                if ('username' in params) and ('key' in params):
                    username = params['username']
                    key = params['key']
                    if not username in self.user_keys.keys():
                        return web.Response(text="Error: invalid username provided.", status=404)
                    # Authenticate the user.
                    if self.auth_password(username, key):
                        use_auth = True
                    else:
                        return web.Response(text="Authentication error.", status=403)
                else:
                    return web.Response(text="Error: some authentication parameters are missing.", status=400)
            else:
                return web.Response(text="Error: authentication parameters were passed in, but this server does not support that feature.", status=500)

        resp = {
            'compute_time': self.user_keys[username]['compute_time'],
            'bandwidth_kb': self.user_keys[username]['bandwidth']
        }

        return web.json_response(resp)

    ####################
    async def remote_sc(self, chip, username):
        '''
        Async method to delegate an '.run()' command to a host,
        and send an email notification when the job completes.
        '''

        # Assemble core job parameters.
        job_hash = chip.status['jobhash']
        top_module = chip.top()
        job_nameid = chip.get('option', 'jobname')

        # Mark the job run as busy.
        if username:
            sc_job_name = f'{username}_{job_hash}_{job_nameid}'
        else:
            sc_job_name = f'{job_hash}_{job_nameid}'
        self.sc_jobs[sc_job_name] = 'busy'

        build_dir = os.path.join(self.nfs_mount, job_hash)
        chip.set('option', 'builddir', build_dir)
        chip.set('option', 'remote', False)
        chip.unset('option', 'credentials')

        os.makedirs(os.path.join(build_dir, 'configs'), exist_ok=True)
        chip.write_manifest(f"{build_dir}/configs/chip{chip.get('option', 'jobname')}.json")

        if self.cfg['cluster']['value'][-1] == 'slurm':
            # Run the job with slurm clustering.
            chip.set('option', 'jobscheduler', 'slurm')

        chip.run()

        # Create a single-file archive to return if results are requested.
        with tarfile.open(os.path.join(self.nfs_mount, f'{job_hash}.tar.gz'), "w:gz") as tar:
            tar.add(os.path.join(self.nfs_mount, job_hash), arcname=job_hash)

        # (Email notifications can be sent here using your preferred API)

        # Mark the job hash as being done.
        self.sc_jobs.pop(sc_job_name)

    ####################
    def auth_password(self, username, password):
        '''
        Helper method to authenticate a username : password combination.
        This minimal implementation of the API uses a simple string match, because
        we don't have a database/signup process/etc for the development server.
        But production server implementations should ALWAYS hash and salt
        passwords before storing them.
        NEVER store production passwords as plaintext!
        '''

        if not username in self.user_keys:
            return False
        return (password == self.user_keys[username]['password'])

    ###################
    @property
    def nfs_mount(self):
        return self.cfg['nfsmount']['value'][-1]

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

    cfg['cluster'] = {
        'short_help': 'Type of compute cluster to use. Valid values: [slurm, local]',
        'switch': '-cluster',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue': ['slurm'],
        'help': ["TBD"]
    }

    cfg['nfsmount'] = {
        'short_help': 'Directory of mounted shared NFS storage.',
        'switch': '-nfs_mount',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue' : ['/nfs/sc_compute'],
        'help' : ["TBD"]
    }

    cfg['auth'] = {
        'short_help': 'Flag determining whether to enable authenticated and encrypted jobs. Intended for testing client-side authentication flags, not for securing sensitive information.',
        'switch': '-auth',
        'switch_args': '<str>',
        'type': ['bool'],
        'defvalue' : [''],
        'help' : ["TBD"]
    }

    return cfg
