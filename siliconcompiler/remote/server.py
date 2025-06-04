# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from aiohttp import web
import copy
import threading
import json
import logging as log
import os
import shutil
import uuid
import tarfile
import sys
import fastjsonschema
from pathlib import Path
from fastjsonschema import JsonSchemaException

import os.path

from siliconcompiler import Chip, Schema
from siliconcompiler.schema import utils as schema_utils
from siliconcompiler._metadata import version as sc_version
from siliconcompiler.schema import SCHEMA_VERSION as sc_schema_version
from siliconcompiler.remote.schema import ServerSchema
from siliconcompiler.remote import banner, JobStatus
from siliconcompiler import NodeStatus as SCNodeStatus
from siliconcompiler.remote import NodeStatus
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler.taskscheduler import TaskScheduler


# Compile validation code for API request bodies.
api_dir = Path(__file__).parent / 'server_schema' / 'requests'

# 'remote_run': Run a stage of a job using the server's cluster settings.
with open(api_dir / 'remote_run.json') as schema:
    validate_remote_run = fastjsonschema.compile(json.loads(schema.read()))

# 'check_progress': Check whether a given job stage is currently running.
with open(api_dir / 'check_progress.json') as schema:
    validate_check_progress = fastjsonschema.compile(json.loads(schema.read()))

# 'check_server': Check whether a given job stage is currently running.
with open(api_dir / 'check_server.json') as schema:
    validate_check_server = fastjsonschema.compile(json.loads(schema.read()))

# 'cancel_job': Cancel a running job.
with open(api_dir / 'cancel_job.json') as schema:
    validate_cancel_job = fastjsonschema.compile(json.loads(schema.read()))

# 'delete_job': Delete a job and remove it from server-side storage.
with open(api_dir / 'delete_job.json') as schema:
    validate_delete_job = fastjsonschema.compile(json.loads(schema.read()))

# 'get_results': Fetch the results of a job run.
# Currently, the 'job_hash' is included in the URL for this call.
with open(api_dir / 'get_results.json') as schema:
    validate_get_results = fastjsonschema.compile(json.loads(schema.read()))


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
    def __init__(self, loglevel="info"):
        '''
        Init method for Server object
        '''

        # Initialize logger
        self.logger = log.getLogger(f'sc_server_{id(self)}')
        handler = log.StreamHandler(stream=sys.stdout)
        formatter = log.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(schema_utils.translate_loglevel(loglevel))

        self.schema = ServerSchema()

        # Set up a dictionary to track running jobs.
        self.sc_jobs_lock = threading.Lock()
        self.sc_jobs = {}
        self.sc_chip_lookup = {}

        # Register callbacks
        TaskScheduler.register_callback("pre_run", self.__run_start)
        TaskScheduler.register_callback("pre_node", self.__node_start)
        TaskScheduler.register_callback("post_node", self.__node_end)

    def __run_start(self, chip):
        flow = chip.get("option", "flow")
        nodes = chip.schema.get("flowgraph", flow, field="schema").get_nodes()

        with self.sc_jobs_lock:
            job_hash = self.sc_chip_lookup[chip]["jobhash"]

        start_tar = os.path.join(self.nfs_mount, job_hash, f'{job_hash}_None.tar.gz')
        start_status = NodeStatus.SUCCESS
        with tarfile.open(start_tar, "w:gz") as tf:
            start_manifest = os.path.join(chip.getworkdir(), f"{chip.design}.pkg.json")
            tf.add(start_manifest, arcname=os.path.relpath(start_manifest, self.nfs_mount))

        with self.sc_jobs_lock:
            job_name = self.sc_chip_lookup[chip]["name"]

            self.sc_jobs[job_name][None]["status"] = start_status

            for step, index in nodes:
                name = f"{step}{index}"
                if name not in self.sc_jobs[job_name]:
                    continue
                self.sc_jobs[job_name][name]["status"] = \
                    chip.get('record', 'status', step=step, index=index)

    def __node_start(self, chip, step, index):
        with self.sc_jobs_lock:
            job_name = self.sc_chip_lookup[chip]["name"]
            self.sc_jobs[job_name][f"{step}{index}"]["status"] = NodeStatus.RUNNING

    def __node_end(self, chip, step, index):
        with self.sc_jobs_lock:
            job_hash = self.sc_chip_lookup[chip]["jobhash"]
            job_name = self.sc_chip_lookup[chip]["name"]

        chip = copy.deepcopy(chip)
        chip.cwd = os.path.join(chip.get('option', 'builddir'), '..')
        with tarfile.open(os.path.join(self.nfs_mount,
                                       job_hash,
                                       f'{job_hash}_{step}{index}.tar.gz'),
                          mode='w:gz') as tf:
            chip._archive_node(tf, step=step, index=index, include="*")

        with self.sc_jobs_lock:
            self.sc_jobs[job_name][f"{step}{index}"]["status"] = \
                chip.get('record', 'status', step=step, index=index)

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
        job_params, response = self._check_request(params['params'],
                                                   validate_remote_run)
        if response is not None:
            return response

        # Create a dummy Chip object to make schema traversal easier.
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

        # Run the job with the configured clustering option. (Non-blocking)
        job_proc = threading.Thread(target=self.remote_sc,
                                    args=[
                                        chip,
                                        job_params['username']])
        job_proc.start()

        # Return a response to the client.
        return web.json_response({'message': f"Starting job: {job_hash}",
                                  'interval': self.checkinterval,
                                  'job_hash': job_hash})

    ####################
    async def handle_get_results(self, request):
        '''
        API handler to redirect 'get_results' POST calls.
        '''

        # Process input parameters
        params = await request.json()
        job_params, response = self._check_request(params,
                                                   validate_get_results)
        job_params['job_hash'] = request.match_info.get('job_hash', '')
        if response is not None:
            return response

        job_hash = job_params['job_hash']
        node = job_params['node'] if 'node' in job_params else None

        zipfn = os.path.join(self.nfs_mount, job_hash, f'{job_hash}_{node}.tar.gz')
        if not os.path.exists(zipfn):
            return web.json_response(
                {'message': 'Could not find results for the requested job/node.'},
                status=404)

        return web.FileResponse(zipfn)

    ####################
    async def handle_delete_job(self, request):
        '''
        API handler for 'delete_job' requests. Delete a job from shared
        cloud compute storage.
        '''

        # Process input parameters
        job_params, response = self._check_request(await request.json(),
                                                   validate_delete_job)
        if response is not None:
            return response

        job_hash = job_params['job_hash']

        # Determine if the job is running.
        with self.sc_jobs_lock:
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
        job_params, response = self._check_request(await request.json(),
                                                   validate_check_progress)
        if response is not None:
            return response

        job_hash = job_params['job_hash']
        username = job_params['username']

        jobname = self.job_name(username, job_hash)

        # Determine if the job is running.
        # TODO: Return information about individual flowgraph nodes.
        with self.sc_jobs_lock:
            if jobname in self.sc_jobs:
                resp = {
                    'status': JobStatus.RUNNING,
                    'message': self.sc_jobs[jobname],
                }
            else:
                resp = {
                    'status': JobStatus.COMPLETED,
                    'message': 'Job has no running steps.',
                }
        return web.json_response(resp)

    ####################
    async def handle_check_server(self, request):
        '''
        API handler for the 'check user' endpoint.
        '''

        # Process input parameters

        job_params, response = self._check_request(await request.json(),
                                                   validate_check_server)
        if response is not None:
            return response

        resp = {
            'status': 'ready',
            'versions': {
                'sc': sc_version,
                'sc_schema': sc_schema_version,
                'sc_server': Server.__version__,
            },
            'progress_interval': self.checkinterval
        }

        username = job_params['username']
        if username:
            resp['user_info'] = {
                'compute_time': self.user_keys[username]['compute_time'],
                'bandwidth_kb': self.user_keys[username]['bandwidth'],
            }

        return web.json_response(resp)

    def job_name(self, username, job_hash):
        if username:
            return f'{username}_{job_hash}'
        else:
            return job_hash

    ####################
    def remote_sc(self, chip, username):
        '''
        Async method to delegate an '.run()' command to a host,
        and send an email notification when the job completes.
        '''

        # Assemble core job parameters.
        job_hash = chip.get('record', 'remoteid')

        runtime = RuntimeFlowgraph(
            chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
            from_steps=chip.get('option', 'from'),
            to_steps=chip.get('option', 'to'),
            prune_nodes=chip.get('option', 'prune'))

        nodes = {}
        nodes[None] = {
            "status": SCNodeStatus.PENDING
        }
        for step, index in runtime.get_nodes():
            status = chip.get('record', 'status', step=step, index=index)
            if not status:
                status = SCNodeStatus.PENDING
            if SCNodeStatus.is_done(status):
                status = NodeStatus.UPLOADED
            nodes[f"{step}{index}"] = {
                "status": status
            }

        # Mark the job run as busy.
        sc_job_name = self.job_name(username, job_hash)
        with self.sc_jobs_lock:
            self.sc_chip_lookup[chip] = {
                "name": sc_job_name,
                "jobhash": job_hash
            }
            self.sc_jobs[sc_job_name] = nodes

        build_dir = os.path.join(self.nfs_mount, job_hash)
        chip.set('option', 'builddir', build_dir)
        chip.set('option', 'remote', False)

        if self.get('option', 'cluster') == 'slurm':
            # Run the job with slurm clustering.
            chip.set('option', 'scheduler', 'name', 'slurm')

        # Run the job.
        chip.run()

        # Mark the job hash as being done.
        with self.sc_jobs_lock:
            self.sc_jobs.pop(sc_job_name)
            self.sc_chip_lookup.pop(chip)

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

    def _check_request(self, request, json_validator):
        params = {}
        if request:
            try:
                params = json_validator(request)
            except JsonSchemaException as e:
                return (params, self.__response(f"Error: Invalid parameters: {e}.", status=400))

            if not request:
                return (params, self.__response("Error: Invalid parameters.", status=400))

        # Check for authentication parameters.
        if self.get('option', 'auth'):
            if ('username' in params) and ('key' in params):
                # Authenticate the user.
                if not self.__auth_password(params['username'], params['key']):
                    return (params, self.__response("Authentication error.", status=403))

            else:
                return (params,
                        self.__response("Error: some authentication parameters are missing.",
                                        status=400))

        if 'username' not in params:
            params['username'] = None

        return (params, None)

    ###################
    def __response(self, message, status=200):
        return web.json_response({'message': message}, status=status)

    ###################
    @property
    def nfs_mount(self):
        # Ensure that NFS mounting path is absolute.
        return os.path.abspath(self.get('option', 'nfsmount'))

    ###################
    @property
    def checkinterval(self):
        return self.get('option', 'checkinterval')

    def get(self, *keypath, field='value'):
        return self.schema.get(*keypath, field=field)

    def set(self, *args, field='value', clobber=True):
        keypath = args[:-1]
        value = args[-1]

        if keypath == ['option', 'loglevel'] and field == 'value':
            self.logger.setLevel(schema_utils.translate_loglevel(value))

        self.schema.set(*keypath, value, field=field, clobber=clobber)

    def write_configuration(self, filepath):
        self.schema.write_manifest(filepath)
