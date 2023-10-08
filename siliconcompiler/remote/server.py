# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from aiohttp import web
import asyncio
import json
import logging as log
import os
import re
import shutil
import uuid
import tarfile
import sys

from siliconcompiler import Chip, Schema
from siliconcompiler._metadata import version as sc_version
from siliconcompiler.schema import SCHEMA_VERSION as sc_schema_version
from siliconcompiler.remote.schema import ServerSchema
from siliconcompiler.remote import banner


class Server:
    """
    The core class for the siliconcompiler 'gateway' server, which can run
    locally or on a remote host. Its job is to process requests for
    asynchronous siliconcompiler jobs, by using the slurm HPC daemon to
    schedule work on available compute nodes. It can also be configured to
    launch new compute nodes in the cloud, for on-demand jobs.
    """

    __version__ = '0.0.1'

    ####################
    def __init__(self, loglevel="INFO"):
        '''
        Init method for Server object
        '''

        # Initialize logger
        self.logger = log.getLogger(f'sc_server_{id(self)}')
        handler = log.StreamHandler(stream=sys.stdout)
        formatter = log.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(loglevel)

        self.schema = ServerSchema(logger=self.logger)

        # Set up a dictionary to track running jobs.
        self.sc_jobs = {}

    def run(self):
        if not os.path.exists(self.nfs_mount):
            raise FileNotFoundError(f'{self.nfs_mount} could not be found.')

        self.logger.info(f"Running in: {self.nfs_mount}")
        # If authentication is enabled, try connecting to the SQLite3 database.
        # (An empty one will be created if it does not exist.)

        # If authentication is enabled, load [username : password/key] mappings.
        # Remember, this development server is intended to be a minimal
        # demonstration of the API, and should only be used for testing purposes.
        # You should NEVER store plaintext passwords in a production
        # server implementation.
        if self.get('option', 'auth'):
            self.user_keys = {}
            json_path = os.path.join(self.nfs_mount, 'users.json')
            try:
                with open(json_path, 'r') as users_file:
                    users_json = json.loads(users_file.read())
                for mapping in users_json['users']:
                    username = mapping['username']
                    self.user_keys[username] = {
                        'password': mapping['password'],
                        'compute_time': 0,
                        'bandwidth': 0
                    }
                    if 'compute_time' in mapping:
                        self.user_keys[username]['compute_time'] = mapping['compute_time']
                    if 'bandwidth' in mapping:
                        self.user_keys[username]['bandwidth'] = mapping['bandwidth']
            except Exception:
                self.logger.warning("Could not find well-formatted 'users.json' "
                                    "file in the server's working directory. "
                                    "(User : Key) mappings were not imported.")

        # Create a minimal web server to process the 'remote_run' API call.
        self.app = web.Application()
        self.app.add_routes([
            web.post('/remote_run/', self.handle_remote_run),
            web.post('/check_progress/', self.handle_check_progress),
            web.post('/check_server/', self.handle_check_server),
            web.post('/delete_job/', self.handle_delete_job),
            web.post('/get_results/{job_hash}.tar.gz', self.handle_get_results),
        ])
        # TODO: Put zip files in a different directory.
        # For security reasons, this is not a good public-facing solution.
        # There's no access control on which files can be downloaded.
        # But this is an example server which only implements a minimal API.
        self.app.router.add_static('/get_results/', self.nfs_mount)

        # Start the async server.
        web.run_app(self.app, port=self.get('option', 'port'))

    def create_cmdline(self, progname, description=None, switchlist=None, additional_args=None):
        def print_banner():
            print(banner)
            print("Version:", Server.__version__, "\n")
            print("-" * 80)

        return self.schema.create_cmdline(
            progname=progname,
            description=description,
            switchlist=switchlist,
            input_map=None,
            additional_args=additional_args,
            version=Server.__version__,
            print_banner=print_banner,
            logger=self.logger)

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

                if 'chip_cfg' not in params:
                    return self.__response('Manifest not provided.', status=400)
                chip_cfg = params['chip_cfg']

        # Process input parameters
        job_params, response = self.__check_request(params['params'],
                                                    require_job_hash=False)
        if response is not None:
            return response

        # Create a dummy Chip object to make schema traversal easier.
        # TODO: if this is a dummy Chip we should be able to use Schema class,
        # but looks like it relies on chip.status.
        # start with a dummy name, as this will be overwritten
        chip = Chip('server')
        # Add provided schema
        chip.schema = Schema(cfg=chip_cfg)

        # Fetch some common values.
        design = chip.design
        job_name = chip.get('option', 'jobname')
        job_hash = uuid.uuid4().hex
        chip.set('record', 'remoteid', job_hash)

        # Ensure that the job's root directory exists.
        job_root = os.path.join(self.nfs_mount, job_hash)
        job_dir = os.path.join(job_root, design, job_name)
        os.makedirs(job_dir, exist_ok=True)

        # Move the uploaded archive and un-zip it.
        # (Contents will be encrypted for authenticated jobs)
        with tarfile.open(tmp_file, "r:gz") as tar:
            tar.extractall(path=job_dir)

        # Delete the temporary file if it still exists.
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        # Create the working directory for the given 'job hash' if necessary.
        chip.set('option', 'builddir', job_root)

        # Remove 'remote' JSON config value to run locally on compute node.
        chip.set('option', 'remote', False)

        # Write JSON config to shared compute storage.
        os.makedirs(os.path.join(job_root, 'configs'), exist_ok=True)

        # Run the job with the configured clustering option. (Non-blocking)
        asyncio.ensure_future(self.remote_sc(chip, job_params['username']))

        # Return a response to the client.
        return web.json_response({'message': f"Starting job: {job_hash}",
                                  'interval': 30,
                                  'job_hash': job_hash})

    ####################
    async def handle_get_results(self, request):
        '''
        API handler to redirect 'get_results' POST calls.
        '''

        # Process input parameters
        params = await request.json()
        params['job_hash'] = request.match_info.get('job_hash', '')
        job_params, response = self.__check_request(params, accept_node=True)
        if response is not None:
            return response

        job_hash = job_params['job_hash']
        node = job_params['node'] if 'node' in job_params else ''

        resp = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'application/x-tar',
                'Content-Disposition': f'attachment; filename="{job_hash}_{node}.tar.gz"'
            },
        )
        await resp.prepare(request)

        zipfn = os.path.join(self.nfs_mount, job_hash, f'{job_hash}_{node}.tar.gz')
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

        # Process input parameters
        job_params, response = self.__check_request(await request.json())
        if response is not None:
            return response

        job_hash = job_params['job_hash']

        # Determine if the job is running.
        for job in self.sc_jobs:
            if job_hash in job:
                return self.__response("Error: job is still running.", status=400)

        # Delete job hash directory, only if it exists.
        # TODO: This assumes no malicious input.
        # Again, we will need a more mature server framework to implement
        # good access control and security policies for a public-facing service.
        build_dir = os.path.join(self.nfs_mount, job_hash)
        check_dir = os.path.dirname(build_dir)
        if check_dir == self.nfs_mount:
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

        # Process input parameters
        job_params, response = self.__check_request(await request.json())
        if response is not None:
            return response

        job_hash = job_params['job_hash']
        username = job_params['username']

        # Determine if the job is running.
        # TODO: Return information about individual flowgraph nodes.
        if "%s%s" % (username, job_hash) in self.sc_jobs:
            resp = {
                'status': 'running',
                'message': 'Job is currently running on the server.',
            }
        else:
            resp = {
                'status': 'completed',
                'message': 'Job has no running steps.',
            }
        return web.json_response(resp)

    ####################
    async def handle_check_server(self, request):
        '''
        API handler for the 'check user' endpoint.
        '''

        # Process input parameters
        job_params, response = self.__check_request(await request.json(), require_job_hash=False)
        if response is not None:
            return response

        resp = {
            'status': 'ready',
            'versions': {
                'sc': sc_version,
                'sc_schema': sc_schema_version,
                'sc_server': Server.__version__,
            },
        }

        username = job_params['username']
        if username:
            resp['user_info'] = {
                'compute_time': self.user_keys[username]['compute_time'],
                'bandwidth_kb': self.user_keys[username]['bandwidth'],
            }

        return web.json_response(resp)

    ####################
    async def remote_sc(self, chip, username):
        '''
        Async method to delegate an '.run()' command to a host,
        and send an email notification when the job completes.
        '''

        # Assemble core job parameters.
        job_hash = chip.get('record', 'remoteid')
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

        os.makedirs(os.path.join(build_dir, 'configs'), exist_ok=True)
        chip.write_manifest(f"{build_dir}/configs/chip{chip.get('option', 'jobname')}.json")

        if self.get('option', 'cluster') == 'slurm':
            # Run the job with slurm clustering.
            chip.set('option', 'scheduler', 'name', 'slurm')

        # Run the job.
        chip.run()

        # Archive each task.
        for (step, index) in chip.nodes_to_execute():
            chip.cwd = os.path.join(chip.get('option', 'builddir'), '..')
            tf = tarfile.open(os.path.join(self.nfs_mount,
                                           job_hash,
                                           f'{job_hash}_{step}{index}.tar.gz'),
                              mode='w:gz')
            chip._archive_node(tf, step=step, index=index)
            tf.close()

        # (Email notifications can be sent here using your preferred API)

        # Mark the job hash as being done.
        self.sc_jobs.pop(sc_job_name)

    ####################
    def __auth_password(self, username, password):
        '''
        Helper method to authenticate a username : password combination.
        This minimal implementation of the API uses a simple string match, because
        we don't have a database/signup process/etc for the development server.
        But production server implementations should ALWAYS hash and salt
        passwords before storing them.
        NEVER store production passwords as plaintext!
        '''

        if username not in self.user_keys:
            return False
        return password == self.user_keys[username]['password']

    def __check_request(self, request, require_job_hash=True, accept_node=False):
        params = {}

        if require_job_hash:
            # Get the job hash value, and verify it is a 32-char hex string.
            if 'job_hash' not in request:
                return (params, self.__response("Error: no job hash provided.", status=400))

            if not re.match("^[0-9A-Za-z]{32}$", request['job_hash']):
                return (params, self.__response("Error: invalid job hash.", status=400))

            params['job_hash'] = request['job_hash']

        # Check for authentication parameters.
        params['username'] = None
        if self.get('option', 'auth'):
            if ('username' in request) and ('key' in request):
                # Authenticate the user.
                if not self.__auth_password(request['username'], request['key']):
                    return (params, self.__response("Authentication error.", status=403))

                params['username'] = request['username']
            else:
                return (params,
                        self.__response("Error: some authentication parameters are missing.",
                                        status=400))

        if accept_node and ('node' in request):
            params['node'] = request['node']

        return (params, None)

    ###################
    def __response(self, message, status=200):
        return web.json_response({'message': message}, status=status)

    ###################
    @property
    def nfs_mount(self):
        # Ensure that NFS mounting path is absolute.
        return os.path.abspath(self.get('option', 'nfsmount'))

    def get(self, *keypath, field='value'):
        return self.schema.get(*keypath, field=field)

    def set(self, *args, field='value', clobber=True):
        keypath = args[:-1]
        value = args[-1]

        if keypath == ['option', 'loglevel'] and field == 'value':
            self.logger.setLevel(value)

        self.schema.set(*keypath, value, field=field, clobber=clobber)

    def write_configuration(self, filepath):
        with open(filepath, 'w') as f:
            self.schema.write_json(f)
