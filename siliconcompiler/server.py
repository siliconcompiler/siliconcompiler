# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
from aiohttp import web
import asyncio
import base64
import json
import logging as log
import os
import re
import subprocess
import shutil
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from siliconcompiler import Chip

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

        # If authentication is enabled, load [username : public key] mappings.
        if self.cfg['auth']['value'][-1]:
            self.user_keys = {}
            json_path = self.cfg['nfsmount']['value'][-1] + '/users.json'
            try:
                with open(json_path, 'r') as users_file:
                    users_json = json.loads(users_file.read())
                for mapping in users_json['users']:
                    self.user_keys[mapping['username']] = mapping['pub_key']
            except:
                self.logger.warning("Could not find well-formatted 'users.json' "\
                                    "file in the server's working directory. "\
                                    "(User : Key) mappings were not imported.")

        # Create a minimal web server to process the 'remote_run' API call.
        self.app = web.Application()
        self.app.add_routes([
            web.post('/remote_run/', self.handle_remote_run),
            web.post('/import/', self.handle_import),
            web.post('/check_progress/', self.handle_check_progress),
            web.post('/delete_job/', self.handle_delete_job),
            web.post('/get_results/{job_hash}.zip', self.handle_get_results),
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

        # Retrieve JSON config from the request body.
        cfg = await request.json()
        params = cfg['params']
        cfg = cfg['chip_cfg']
        if not 'job_hash' in params:
            return web.Response(text="Error: no job hash provided.")
        job_hash = params['job_hash']

        # Retrieve authentication parameters if enabled.
        use_auth = False
        if ('username' in params) or ('key' in params):
            if self.cfg['auth']['value'][-1]:
                if ('username' in params) and ('key' in params):
                    username = params['username']
                    key = params['key']
                    if not username in self.user_keys.keys():
                        return web.Response(text="Error: invalid username provided.")
                    # Authenticate the user.
                    if self.auth_userkey(username, key):
                        use_auth = True
                    else:
                        return web.Response(text="Authentication error.")
                else:
                    return web.Response(text="Error: some authentication parameters are missing.")
            else:
                return web.Response(text="Error: authentication parameters were passed in, but this server does not support that feature.")

        # Create a dummy Chip object to make schema traversal easier.
        chip = Chip()
        chip.cfg = cfg

        # Reset 'build' directory in NFS storage.
        build_dir = '%s/%s'%(self.cfg['nfsmount']['value'][-1], job_hash)
        jobs_dir = '%s/%s'%(build_dir, chip.get('design'))
        cur_id = chip.get('jobid')
        job_nameid = f"{chip.get('jobname')}{cur_id}"

        # Create the working directory for the given 'job hash' if necessary.
        subprocess.run(['mkdir', '-p', jobs_dir])
        chip.set('dir', build_dir, clobber=True)
        # Link to the 'import' directory if necessary.
        subprocess.run(['mkdir', '-p', '%s/%s'%(jobs_dir, job_nameid)])
        subprocess.run(['ln', '-s', '%s/import0'%build_dir, '%s/%s/import0'%(jobs_dir, job_nameid)])

        # Remove 'remote' JSON config value to run locally on compute node.
        chip.set('remote', 'addr', '', clobber=True)
        # Rename source files in the config dict; the 'import' step already
        # ran and collected the sources into a single Verilog file.
        chip.set('source', '%s/import0/outputs/%s.v'%(build_dir, chip.get('design')), clobber=True)

        # Write JSON config to shared compute storage.
        subprocess.run(['mkdir', '-p', '%s/configs'%build_dir])
        chip.writecfg('%s/configs/chip%s.json'%(build_dir, cur_id))

        # Run the job with the configured clustering option. (Non-blocking)
        if use_auth:
            asyncio.create_task(self.remote_sc_auth(chip,
                                                    username,
                                                    key))
        else:
            asyncio.create_task(self.remote_sc(chip))

        # Return a response to the client.
        response_text = f"Starting job: {job_hash}"
        return web.Response(text=response_text)

    ####################
    async def handle_import(self, request):
        '''
        API handler for 'import' requests. Accepts a file archive upload,
        which the server extracts into shared compute cluster storage in
        preparation for running a remote job stage.

        TODO: Infer file type from file extension. Currently only supports .zip
        '''

        # Receive and parse the POST request body.
        use_auth = False
        tmp_file = self.cfg['nfsmount']['value'][-1] + '/' + uuid.uuid4().hex
        reader = await request.multipart()
        while True:
            part = await reader.next()
            if part is None:
                break
            # If the data is encrypted, it is sent in a '.crypt' file. If not,
            # it is sent in a '.zip' archive. Either way, stream the file to disk.
            if part.name == 'import':
                # job hash may not be available yet; it's also sent in the body.
                with open(tmp_file, 'wb') as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
            elif part.name == 'params':
                # Get the job parameters.
                job_params = await part.json()
                # Get the job hash value, and verify it is a 32-char hex string.
                if not 'job_hash' in job_params:
                    return web.Response(text="Error: no job hash provided.")
                job_hash = job_params['job_hash']
                if not re.match("^[0-9A-Za-z]{32}$", job_hash):
                    return web.Response(text="Error: invalid job hash.")
                # Get the job's name.
                if not 'job_name' in job_params:
                    return web.Response(text="Error: no job name provided.")
                job_name = job_params['job_name']
                # Check for authentication parameters.
                if ('username' in job_params) or ('key' in job_params) or ('aes_key' in job_params) or ('aes_iv' in job_params):
                    if self.cfg['auth']['value'][-1]:
                        if ('username' in job_params) and ('key' in job_params) and ('aes_key' in job_params) and ('aes_iv' in job_params):
                            username = job_params['username']
                            key = job_params['key']
                            aes_key = job_params['aes_key']
                            aes_iv = job_params['aes_iv']
                            if not username in self.user_keys.keys():
                                return web.Response(text="Error: invalid username provided.")
                            # Authenticate the user.
                            if self.auth_userkey(username, key):
                                use_auth = True
                            else:
                                return web.Response(text="Authentication error.")
                        else:
                            return web.Response(text="Error: some authentication parameters are missing.")
                    else:
                        return web.Response(text="Error: authentication parameters were passed in, but this server does not support that feature.")

                # Ensure that the job's root directory exists.
                job_root = '%s/%s'%(self.cfg['nfsmount']['value'][-1], job_hash)
                subprocess.run(['mkdir', '-p', job_root])

                if use_auth:
                    # Move the encrypted archive, and save the AES cipher info.
                    os.replace(tmp_file, '%s/import.crypt'%job_root)
                    with open('%s/import.bin'%job_root, 'wb+') as encrypted_key:
                        encrypted_key.write(base64.urlsafe_b64decode(aes_key))
                    with open('%s/import.iv'%job_root, 'wb+') as encrypted_key:
                        encrypted_key.write(base64.urlsafe_b64decode(aes_iv))
                else:
                    # Ensure that the required directories exists.
                    subprocess.run(['mkdir', '-p', '%s/import0'%job_root])
                    # Move the uploaded archive and un-zip it.
                    os.replace(tmp_file, '%s/import.zip'%job_root)
                    subprocess.run(['unzip', '-o', '%s/import.zip'%(job_root)], cwd=job_root)

        # Delete the temporary file if it still exists.
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        # Done.
        return web.Response(text="Successfully imported project %s."%job_hash)

    ####################
    async def handle_get_results(self, request):
        '''
        API handler to redirect 'get_results' POST calls.

        '''

        # Retrieve the job hash.
        job_hash = request.match_info.get('job_hash', None)
        if not job_hash:
            return web.Response(text="Error: no job hash provided.")

        # Redirect to the same URL, but with a GET request.
        return web.HTTPSeeOther(request.url)

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
        job_hash = chip.get('remote', 'jobhash')
        top_module = chip.get('design')
        job_nameid = f"{chip.get('jobname')}{chip.get('jobid')}"

        # Mark the job run as busy.
        self.sc_jobs["%s%s_0"%(username, job_hash)] = 'busy'

        # Reset 'build' directory in NFS storage.
        build_dir = '/tmp/%s_%s'%(job_hash, job_nameid)
        jobs_dir = '%s/%s'%(build_dir, top_module)
        os.mkdir(build_dir)
        chip.set('dir', build_dir, clobber=True)

        # Copy the 'import' directory for a new run if necessary.
        nfs_mount = self.cfg['nfsmount']['value'][-1]
        if not os.path.isfile('%s/%s/%s.crypt'%(nfs_mount, job_hash, job_nameid)):
            shutil.copy('%s/%s/import.crypt'%(nfs_mount, job_hash),
                        '%s/%s/%s.crypt'%(nfs_mount, job_hash, job_nameid))
            # Also copy the iv nonce for decryption.
            # New initialization vectors are generated before each *encrypt* step.
            shutil.copy('%s/%s/import.iv'%(nfs_mount, job_hash),
                        '%s/%s/%s.iv'%(nfs_mount, job_hash, job_nameid))

        # Rename source files in the config dict; the 'import' step already
        # ran and collected the sources into a single Verilog file.
        chip.set('source', f"${build_dir}/{top_module}/{job_nameid}/import0/outputs/{top_module}.v", clobber=True)

        run_cmd = ''
        if self.cfg['cluster']['value'][-1] == 'slurm':
            # TODO: support encrypted jobs on a slurm cluster.
            pass
        else:
            # Run the build command locally.
            from_dir = '%s/%s'%(nfs_mount, job_hash)
            to_dir   = '/tmp/%s_%s'%(job_hash, job_nameid)
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
                keyfile.write(base64.urlsafe_b64decode(pk).decode())
            chip.set('remote', 'key', keypath, clobber=True)
            chip.writecfg(f"{build_dir}/configs/chip0.json")
            # Create the command to run.
            run_cmd  = '''cp %s/%s.crypt %s/%s.crypt ;
                          cp %s/%s.iv %s/%s.iv ;
                          cp %s/import.bin %s/import.bin ;
                          sc -cfg %s/configs/chip0.json ;
                          cp %s/%s.crypt %s/%s.crypt ;
                          cp %s/%s.iv %s/%s.iv ;
                          rm -rf %s
                       '''%(from_dir, job_nameid, to_dir, job_nameid,
                            from_dir, job_nameid, to_dir, job_nameid,
                            from_dir, to_dir,
                            build_dir,
                            to_dir, job_nameid, from_dir, job_nameid,
                            to_dir, job_nameid, from_dir, job_nameid,
                            to_dir)

            # Run the generated command.
            subprocess.run(run_cmd, shell = True)

            # Ensure that the private key file was deleted.
            # (The whole directory should already be gone,
            #  but the subprocess command could fail)
            if os.path.isfile(keypath):
                os.remove(keypath)

        # Zip results after all job stages have finished.
        subprocess.run(['zip',
                        '-r',
                        '%s.zip'%job_hash,
                        '%s'%job_hash],
                       cwd = nfs_mount)

        # (Email notifications can be sent here using your preferred API)

        # Mark the job hash as being done.
        self.sc_jobs.pop("%s%s_0"%(username, job_hash))

    ####################
    async def remote_sc(self, chip):
        '''
        Async method to delegate an 'sc' command to a slurm host,
        and send an email notification when the job completes.
        '''

        # Collect a few bookkeeping values.
        job_hash = chip.get('remote', 'jobhash')
        top_module = chip.get('design')
        sc_sources = chip.get('source')
        build_dir = chip.get('dir')
        jobid = chip.get('jobid')

        # Mark the job hash as being busy.
        self.sc_jobs["%s_%s"%(job_hash, jobid)] = 'busy'

        run_cmd = ''
        if self.cfg['cluster']['value'][-1] == 'slurm':
            # Assemble the 'sc' command. The host must be running slurmctld.
            # TODO: Avoid using a hardcoded $PATH variable for the compute node.
            export_path  = '--export=PATH=/home/ubuntu/OpenROAD-flow-scripts/tools/build/OpenROAD/src'
            export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/TritonRoute'
            export_path += ':/home/ubuntu/OpenROAD-flow-scripts/tools/build/yosys/bin'
            export_path += ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin'
            # Send JSON config instead of using subset of flags.
            # TODO: Use slurmpy SDK?
            run_cmd  = 'srun %s sc '%(export_path)
            run_cmd += '-cfg %s/configs/chip%s.json '%(build_dir, jobid)
        else:
            # Unrecognized or unset clusering option; run locally on the
            # server itself. (Note: local runs are mostly synchronous, so
            # this will probably block the server from responding to other
            # calls. It should only be used for testing and development.)
            run_cmd = 'sc -cfg %s/configs/chip%s.json'%(build_dir, jobid)

        # Create async subprocess shell, and block this thread until it finishes.
        proc = await asyncio.create_subprocess_shell(run_cmd)
        await proc.wait()

        # (Email notifications can be sent here using SES)

        # Create a single-file archive to return if results are requested.
        subprocess.run(['zip',
                        '-r',
                        '%s.zip'%job_hash,
                        '%s'%job_hash],
                       cwd=self.cfg['nfsmount']['value'][-1])

        # Mark the job hash as being done.
        self.sc_jobs.pop("%s_%s"%(job_hash, jobid))

    ####################
    def auth_userkey(self, username, private_key, enc='b64'):
        '''Helper method to authenticate that a provided private key 'matches'
           a stored public key. So, the private key must correctly decrypt
           data which was encrypted using the public key.
        '''

        try:
            # Get the user's public key.
            if username in self.user_keys:
                pubkey = self.user_keys[username]
            else:
                return False

            if enc == 'b64':
                # Decode base-64 value.
                pk_str = base64.b64decode(private_key).decode()
            else:
                # Unknown encoding; treat it as a string.
                pk_str = private_key

            # Create cipher objects for the public and private keys.
            encrypt_key = serialization.load_ssh_public_key(
                pubkey.encode(),
                backend=default_backend())
            decrypt_key = serialization.load_ssh_private_key(
                pk_str.encode(),
                None,
                backend=default_backend())

            # Encrypt a test string using the public key.
            nonce = uuid.uuid4().hex
            test_encrypt = encrypt_key.encrypt(
                nonce.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA512()),
                    algorithm=hashes.SHA512(),
                    label=None,
                ))

            # Check that the message decrypts correctly using the private key.
            test_decrypt = decrypt_key.decrypt(
                test_encrypt,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA512()),
                    algorithm=hashes.SHA512(),
                    label=None,
                ))

            # Authentication succeeds if decrypted nonce matches the original.
            return (test_decrypt and (test_decrypt.decode() == nonce))
        except:
            # Authentication fails if any unexpected errors occur.
            return False

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
