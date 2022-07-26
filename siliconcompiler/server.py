# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
from aiohttp import web
import asyncio
import base64
import glob
import json
import logging as log
import os
import re
import subprocess
import shutil
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from siliconcompiler import Chip
from siliconcompiler.crypto import decrypt_job, gen_cipher_key

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
        # Ensure that NFS mounting path is absolute.
        self.cfg['nfsmount']['value'] = [os.path.abspath(self.cfg['nfsmount']['value'][-1])]

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
            json_path = self.cfg['nfsmount']['value'][-1] + '/users.json'
            try:
                with open(json_path, 'r') as users_file:
                    users_json = json.loads(users_file.read())
                for mapping in users_json['users']:
                    self.user_keys[mapping['username']] = {
                        'pub_key': mapping['pub_key'],
                        'priv_key': mapping['priv_key'],
                        'password': mapping['password'],
                    }
            except:
                self.logger.warning("Could not find well-formatted 'users.json' "\
                                    "file in the server's working directory. "\
                                    "(User : Key) mappings were not imported.")

        # Create a minimal web server to process the 'remote_run' API call.
        self.app = web.Application()
        self.app.add_routes([
            web.post('/remote_run/', self.handle_remote_run),
            web.post('/check_progress/', self.handle_check_progress),
            web.post('/delete_job/', self.handle_delete_job),
            web.post('/get_results/{job_hash}.tar.gz', self.handle_get_results),
        ])
        # TODO: Put zip files in a different directory.
        # For security reasons, this is not a good public-facing solution.
        # There's no access control on which files can be downloaded.
        # But this is an example server which only implements a minimal API.
        self.app.router.add_static('/get_results/', self.cfg['nfsmount']['value'][0])

        # Start the async server.
        web.run_app(self.app, port = int(self.cfg['port']['value'][-1]))

    ####################
    async def handle_remote_run(self, request):
        '''
        API handler for 'remote_run' commands. This method delegates
        a 'Chip.run(...)' method to a compute node using slurm.
        '''

        # Temporary file path to store streamed data.
        tmp_file = self.cfg['nfsmount']['value'][-1] + '/' + uuid.uuid4().hex

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
        chip = Chip(cfg['design']['value'])
        chip.cfg = cfg

        # Fetch some common values.
        design = chip.get('design')
        job_name = chip.get('option', 'jobname')
        job_nameid = f'{job_name}'
        chip.status['jobhash'] = job_hash

        # Ensure that the job's root directory exists.
        job_root = f"{self.cfg['nfsmount']['value'][-1]}/{job_hash}"
        job_dir  = f"{job_root}/{design}/{job_name}"
        subprocess.run(['mkdir', '-p', job_dir])

        if use_auth:
            # Create a new AES block cipher key, and an IV for the import step.
            decrypt_key = serialization.load_ssh_private_key(self.user_keys[username]['priv_key'].encode(), None, backend=default_backend())
            gen_cipher_key(job_dir, self.user_keys[username]['pub_key'], pubk_type='str')
            # Decrypt the block cipher key.
            with open(os.path.join(job_dir, 'import.bin'), 'rb') as f:
                aes_key = decrypt_key.decrypt(
                    f.read(),
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA512()),
                        algorithm=hashes.SHA512(),
                        label=None,
                    ))
            aes_iv  = os.urandom(16)
            with open(os.path.join(job_dir, f'import.iv'), 'wb') as f:
                f.write(aes_iv)
            # Encrypt the received data.
            cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
            encryptor = cipher.encryptor()
            with open(os.path.join(job_dir, f'import.crypt'), 'wb') as wf:
                with open(tmp_file, 'rb') as rf:
                    while True:
                        chunk = rf.read(1024)
                        if not chunk:
                            break
                        wf.write(encryptor.update(chunk))
                    wf.write(encryptor.finalize())
        else:
            # Move the uploaded archive and un-zip it.
            # (Contents will be encrypted for authenticated jobs)
            os.replace(tmp_file, '%s/import.tar.gz'%job_root)
            subprocess.run(['tar', '-xzf', '%s/import.tar.gz'%(job_root)],
                           cwd=job_dir)

        # Delete the temporary file if it still exists.
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        # Reset 'build' directory in NFS storage.
        build_dir = '%s/%s'%(self.cfg['nfsmount']['value'][-1], job_hash)
        jobs_dir = '%s/%s'%(build_dir, chip.get('design'))
        job_nameid = f"{chip.get('option', 'jobname')}"

        # Create the working directory for the given 'job hash' if necessary.
        subprocess.run(['mkdir', '-p', jobs_dir])
        chip.set('option', 'builddir', build_dir, clobber=True)
        # Link to the 'import' directory if necessary.
        subprocess.run(['mkdir', '-p', '%s/%s'%(jobs_dir, job_nameid)])
        #subprocess.run(['ln', '-s', '%s/import0'%build_dir, '%s/%s/import0'%(jobs_dir, job_nameid)])

        # Remove 'remote' JSON config value to run locally on compute node.
        chip.set('option', 'remote', False, clobber=True)
        chip.set('option', 'credentials', '', clobber=True)

        # Write JSON config to shared compute storage.
        subprocess.run(['mkdir', '-p', '%s/configs'%build_dir])

        # Run the job with the configured clustering option. (Non-blocking)
        if use_auth:
            asyncio.ensure_future(self.remote_sc_auth(chip,
                                                      username,
                                                      self.user_keys[username]['priv_key']))
        else:
            asyncio.ensure_future(self.remote_sc(chip))

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

        zipfn = os.path.join(self.cfg['nfsmount']['value'][-1], job_hash+'.tar.gz')
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
          build_dir = '%s/%s'%(self.cfg['nfsmount']['value'][0], job_hash)
          if os.path.exists(build_dir):
            #print('Deleting: %s'%build_dir)
            shutil.rmtree(build_dir)
          if os.path.exists('%s.tar.gz'%build_dir):
            #print('Deleting: %s.tar.gz'%build_dir)
            os.remove('%s.tar.gz'%build_dir)

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
    async def remote_sc_auth(self, chip, username, pk):
        '''
        Async method to delegate an 'sc' command to a slurm host,
        and send an email notification when the job completes.
        This method requires authentication to access client-encrypted data,
        but the transport methods for this dev server aren't adequately secured.
        '''

        # Assemble core job parameters.
        job_hash = chip.status['jobhash']
        design = chip.get('design')
        top_module = chip.top()
        job_nameid = f"{chip.get('option', 'jobname')}"
        nfs_mount = self.cfg['nfsmount']['value'][-1]

        # Mark the job run as busy.
        self.sc_jobs[f'{username}{job_hash}_{job_nameid}'] = 'busy'

        # Reset 'build' directory in NFS storage.
        build_dir = '/tmp/%s_%s'%(job_hash, job_nameid)
        os.mkdir(build_dir)

        run_cmd = ''
        if self.cfg['cluster']['value'][-1] == 'slurm':
            # Run the job with slurm clustering.
            chip.set('option', 'builddir', f'{nfs_mount}/{job_hash}', clobber=True)
            chip.set('option', 'jobscheduler', 'slurm')
            chip.set('option', 'remote', False)
            chip.set('option', 'credentials', '', clobber=True)
            chip.status['decrypt_key'] = base64.urlsafe_b64encode(pk)
            chip.run()
        else:
            chip.set('option', 'builddir', build_dir, clobber=True)
            # Run the build command locally.
            from_dir = '%s/%s'%(nfs_mount, job_hash)
            to_dir   = '/tmp/%s_%s'%(job_hash, job_nameid)
            job_dir  = os.path.join(build_dir, top_module, job_nameid)
            # Write plaintext JSON config to the build directory.
            subprocess.run(['mkdir', '-p', to_dir])
            subprocess.run(['mkdir', '-p', '%s/configs'%build_dir])
            # Write private key to a file.
            # This should be okay, because we are already trusting the local
            # "compute node" disk to store the decrypted data. Further, the
            # file will be deleted immediately after the run.
            # Even so, use the usual 400 permissions for key files.
            keypath = f'{to_dir}/pk'
            with open(os.open(keypath, os.O_CREAT | os.O_WRONLY, 0o400), 'w+') as keyfile:
                keyfile.write(pk)
            chip.write_manifest(f"{build_dir}/configs/chip{chip.get('option', 'jobname')}.json")
            # Create the command to run.
            run_cmd  = f"cp -R {from_dir}/* {to_dir}/ ; "
            run_cmd += f"sc-crypt -mode decrypt -target {job_dir} -key_file {keypath} ; "
            run_cmd += f"sc -cfg {build_dir}/configs/chip{chip.get('option', 'jobname')}.json -dir {to_dir} -remote_addr '' ; "
            run_cmd += f"sc-crypt -mode encrypt -target {job_dir} -key_file {keypath} ; "
            run_cmd += f"cp -R {to_dir}/{top_module}/* {from_dir}/{top_module}/ ; "
            run_cmd += f"rm -rf {to_dir}"

            # Run the generated command.
            proc = await asyncio.create_subprocess_shell(run_cmd)
            await proc.wait()

            # Ensure that the private key file was deleted.
            # (The whole directory should already be gone,
            #  but the subprocess command could fail)
            if os.path.isfile(keypath):
                os.remove(keypath)

        # Zip results after all job stages have finished.
        subprocess.run(['tar',
                        '-czf',
                        '%s.tar.gz'%job_hash,
                        '%s'%job_hash],
                       cwd = nfs_mount)

        # (Email notifications can be sent here using your preferred API)

        # Mark the job hash as being done.
        self.sc_jobs.pop(f'{username}{job_hash}_{chip.get("jobname")}')

    ####################
    async def remote_sc(self, chip):
        '''
        Async method to delegate an 'sc' command to a slurm host,
        and send an email notification when the job completes.
        '''

        # Collect a few bookkeeping values.
        job_hash = chip.status['jobhash']
        build_dir = chip.get('option', 'builddir')
        jobid = chip.get('option', 'jobname')

        # Mark the job hash as being busy.
        self.sc_jobs["%s_%s"%(job_hash, jobid)] = 'busy'

        run_cmd = ''
        if self.cfg['cluster']['value'][-1] == 'slurm':
            # Assemble the 'sc' command. The host must be running slurmctld.
            # TODO: Avoid using a hardcoded $PATH variable for the compute node.
            #export_path  = '--export=PATH=/home/ubuntu/OpenROAD-flow-scripts/tools/build/OpenROAD/src'
            #export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/TritonRoute'
            #export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/yosys/bin'
            #export_path += ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin'
            # Send JSON config instead of using subset of flags.
            # TODO: Use slurmpy SDK?
            #run_cmd  = 'srun %s sc '%(export_path)
            #run_cmd += '-cfg %s/configs/chip%s.json '%(build_dir, jobid)
            # Run the job with slurm clustering.
            chip.set('jobscheduler', 'slurm')
            chip.run()
        else:
            # Unrecognized or unset clusering option; run locally on the
            # server itself. (Note: local runs are mostly synchronous, so
            # this will probably block the server from responding to other
            # calls. It should only be used for testing and development.)
            cfg_out = f"{build_dir}/configs/chip{jobid}.json"
            chip.write_manifest(cfg_out)
            run_cmd = f'sc -cfg {cfg_out}'

            # Create async subprocess shell, and block this thread until it finishes.
            proc = await asyncio.create_subprocess_shell(run_cmd)
            await proc.wait()

        # (Email notifications can be sent here using SES)

        # Create a single-file archive to return if results are requested.
        subprocess.run(['tar',
                        '-czf',
                        '%s.tar.gz'%job_hash,
                        '%s'%job_hash],
                       cwd=self.cfg['nfsmount']['value'][-1])

        # Mark the job hash as being done.
        self.sc_jobs.pop("%s_%s"%(job_hash, jobid))

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
