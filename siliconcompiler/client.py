# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import base64
import glob
import math
import multiprocessing
import importlib
import json
import os
import requests
import shutil
import subprocess
import sys
import time
import uuid

from siliconcompiler.crypto import *

###################################
def get_base_url(chip):
    '''Helper method to get the root URL for API calls, given a Chip object.
    '''
    remote_host = chip.get('remote', 'addr')
    remote_port = chip.get('remote', 'port')
    remote_host += ':' + str(remote_port)
    if remote_host.startswith('http'):
        remote_protocol = ''
    else:
        remote_protocol = 'https://' if remote_port == '443' else 'http://'
    return remote_protocol + remote_host

###################################
def remote_preprocess(chip):
    '''Helper method to run a local import stage for remote jobs.
    '''

    # Assign a new 'job_hash' to the chip if necessary.
    if not chip.get('remote', 'jobhash'):
        job_hash = uuid.uuid4().hex
        chip.set('remote', 'jobhash', job_hash)

    manager = multiprocessing.Manager()
    error = manager.dict()
    active = manager.dict()

    # Run any local steps if necessary.
    local_steps = []
    for step in chip.getkeys('flowgraph'):
        if not step in chip.get('remote', 'steplist'):
            local_steps.append(step)

    # Setup up tools for all local functions
    for step in local_steps:
        indexlist = chip.getkeys('flowgraph', step)
        for index in indexlist:
            tool = chip.get('flowgraph', step, index, 'tool')
            # Setting up tool is optional (step may be a builtin function)
            if tool:
                chip.set('arg','step', step)
                chip.set('arg','index', index)
                func = chip.find_function(tool, 'tool', 'setup_tool')
                func(chip)
            # Run the actual import step locally.
            chip._runstep(step, index, active, error)

            # Update constraints with local relative paths, and re-write config files.
            new_constraints = []
            for c in chip.get('constraint'):
                new_constraints.append(f"inputs/{c[(c.rfind('/')+1):]}")
            chip.set('constraint', new_constraints)
            stepindex_workdir = chip._getworkdir(step=step, index=index)
            chip.write_manifest(f'{stepindex_workdir}/outputs/{chip.get("design")}.pkg.json')

    # Set 'steplist' to only the remote steps, for the future server-side run.
    remote_steplist = []
    for step in chip.getkeys('flowgraph'):
        if not step in local_steps:
            remote_steplist.append(step)
    chip.set('steplist', remote_steplist, clobber=True)

###################################
def client_decrypt(chip):
    '''Helper method to decrypt project data before running a job on it.
    '''

    job_path = f"{chip.get('dir')}/{chip.get('design')}/" \
               f"{chip.get('jobname')}{chip.get('jobid')}"
    decrypt_job(job_path,
                chip.get('remote', 'key'))

###################################
def client_encrypt(chip):
    '''Helper method to re-encrypt project data after processing.
    '''

    job_path = f"{chip.get('dir')}/{chip.get('design')}/" \
               f"{chip.get('jobname')}{chip.get('jobid')}"
    encrypt_job(job_path,
                chip.get('remote', 'key'))

###################################
def remote_run(chip):
    '''Helper method to run a job stage on a remote compute cluster.
    Note that files will not be copied to the remote stage; typically
    the source files will be copied into the cluster's storage before
    calling this method.
    If the "-remote" parameter was not passed in, this method
    will print a warning and do nothing.
    This method assumes that the given stage should not be skipped,
    because it is called from within the `Chip.run(...)` method.

    '''

    # Time how long the process has been running for.
    step_start = time.monotonic()

    # Ask the remote server to start processing the requested step.
    request_remote_run(chip)

    # Check the job's progress periodically until it finishes.
    is_busy = True
    while is_busy:
      chip.logger.info("Job is still running. (%d seconds)"%(
                       int(time.monotonic() - step_start)))
      time.sleep(10)
      try:
          is_busy = is_job_busy(chip)
      except:
          # Sometimes an exception is raised if the request library cannot
          # reach the server due to a transient network issue.
          # Retrying ensures that jobs don't break off when the connection drops.
          is_busy = True
          chip.logger.info("Unknown network error encountered: retrying.")
    chip.logger.info("Remote job run completed!")

###################################
def request_remote_run(chip):
    '''Helper method to make a web request to start a job stage.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/remote_run/'

    # Use authentication if necessary.
    job_nameid = f"{chip.get('jobname')}{chip.get('jobid')}"
    post_params = {
        'chip_cfg': chip.cfg,
        'params': {
            'job_hash': chip.get('remote', 'jobhash'),
        }
    }
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        # Encrypt the .zip archive with the user's public key.
        # Asymmetric key cryptography is good at signing values, but bad at
        # encrypting bulk data. One common approach is to generate a random
        # symmetric encryption key, which can be encrypted using the asymmetric
        # keys. Then the data itself can be encrypted with the symmetric cipher.
        # We'll use AES-256-CTR, because the Python 'cryptography' module's
        # recommended 'Fernet' algorithm only works on files that fit in memory.
        pkpath = chip.get('remote', 'key')
        job_path = f"{chip.get('dir')}/{chip.get('design')}/{job_nameid}"

        # AES-encrypt the job data prior to uploading.
        # TODO: This assumes a common OpenSSL convention of using similar file
        # paths for private and public keys: /path/to/key and /path/to/key.pub
        # If the user has the account's private key, it is assumed that they
        # will also have the matching public key in the same locale.
        gen_cipher_key(job_path, f"{os.path.abspath(pkpath)}.pub")
        encrypt_job(job_path, pkpath)

        # Read the key and encode it in base64 format.
        with open(os.path.abspath(pkpath), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['params']['username'] = chip.get('remote', 'user')
        post_params['params']['key'] = b64_key

        # Set up 'temporary cloud host' parameters.
        num_temp_hosts = int(chip.get('remote', 'hosts'))
        if num_temp_hosts > 0:
            post_params['params']['new_hosts'] = num_temp_hosts
            if chip.get('remote', 'ram'):
                post_params['params']['new_host_ram'] = int(chip.get('remote', 'ram'))
            if chip.get('remote', 'threads'):
                post_params['params']['new_host_threads'] = int(chip.get('remote', 'threads'))

    # If '-remote_user' and '-remote_key' are not both specified,
    # no authorizaion is configured; proceed without crypto.
    # If they were specified, these files are now encrypted.
    local_build_dir = stepdir = '/'.join([chip.get('dir'),
                                          chip.get('design'),
                                          job_nameid])
    subprocess.run(['zip',
                    '-r',
                    '-q',
                    'import.zip',
                    '.'],
                   cwd=local_build_dir)
    upload_file = os.path.abspath(f'{local_build_dir}/import.zip')

    # Make the actual request, streaming the bulk data as a multipart file.
    # Redirected POST requests are translated to GETs. This is actually
    # part of the HTTP spec, so we need to manually follow the trail.
    redirect_url = remote_run_url
    while redirect_url:
        with open(upload_file, 'rb') as f:
            resp = requests.post(redirect_url,
                                 files={'import': f,
                                        'params': json.dumps(post_params)},
                                 allow_redirects=False)
            if resp.status_code == 302:
                redirect_url = resp.headers['Location']
            elif resp.status_code >= 400:
                chip.logger.info(resp.text)
                chip.logger.error('Error starting remote job run; quitting.')
                sys.exit(1)
            else:
                chip.logger.info(resp.text)
                return

###################################
def is_job_busy(chip):
    '''Helper method to make an async request asking the remote server
    whether a job is busy, or ready to accept a new step.
    Returns True if the job is busy, False if not.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/check_progress/'

    # Set common parameters.
    post_params = {
        'job_hash': chip.get('remote', 'jobhash'),
        'job_id': str(chip.get('jobid')),
    }

    # Set authentication parameters if necessary.
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['username'] = chip.get('remote', 'user')
        post_params['key'] = b64_key

    # Make the request and print its response.
    redirect_url = remote_run_url
    while redirect_url:
        resp = requests.post(redirect_url,
                             data=json.dumps(post_params),
                             allow_redirects=False)
        if resp.status_code == 302:
            redirect_url = resp.headers['Location']
        else:
            return (resp.text != "Job has no running steps.")

###################################
def delete_job(chip):
    '''Helper method to delete a job from shared remote storage.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/delete_job/'

    # Set common parameter.
    post_params = {
        'job_hash': chip.get('remote', 'jobhash'),
    }

    # Set authentication parameters if necessary.
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['username'] = chip.get('remote', 'user')
        post_params['key'] = b64_key

    # Make the request.
    redirect_url = remote_run_url
    while redirect_url:
        resp = requests.post(redirect_url,
                             data=json.dumps(post_params),
                             allow_redirects=False)
        if resp.status_code == 302:
                redirect_url = resp.headers['Location']
        else:
            response = resp.text
            return response

###################################
def fetch_results_request(chip):
    '''Helper method to fetch job results from a remote compute cluster.
    '''

    # Set the request URL.
    job_hash = chip.get('remote', 'jobhash')
    remote_run_url = get_base_url(chip) + '/get_results/' + job_hash + '.zip'

    # Set authentication parameters if necessary.
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params = {
            'username': chip.get('remote', 'user'),
            'key': b64_key,
        }
    else:
        post_params = {}

    # Make the web request, and stream the results archive in chunks.
    redirect_url = remote_run_url
    can_redirect = False
    while redirect_url:
        with open('%s.zip'%job_hash, 'wb') as zipf:
            resp = requests.post(redirect_url,
                                 data=json.dumps(post_params),
                                 allow_redirects=can_redirect,
                                 stream=True)
            if resp.status_code == 302:
                redirect_url = resp.headers['Location']
            elif resp.status_code == 303:
                redirect_url = resp.headers['Location']
                can_redirect = True
            else:
                shutil.copyfileobj(resp.raw, zipf)
                return

###################################
def fetch_results(chip):
    '''Helper method to fetch and open job results from a remote compute cluster.
    '''

    # Fetch the remote archive after the export stage.
    fetch_results_request(chip)

    # Unzip the results.
    top_design = chip.get('design')
    job_hash = chip.get('remote', 'jobhash')
    job_nameid = f"{chip.get('jobname')}{chip.get('jobid')}"
    subprocess.run(['unzip', '-q', f'{job_hash}.zip'])
    # Remove the results archive after it is extracted.
    os.remove(f'{job_hash}.zip')

    # Call 'delete_job' to remove the run from the server.
    delete_job(chip)

    # For encrypted jobs each permutation's result is encrypted in its own archive.
    # For unencrypted jobs, results are simply stored in the archive.
    if ('key' in chip.getkeys('remote')) and chip.get('remote', 'key'):
        # Decrypt the job data.
        decrypt_job(f"{job_hash}/{chip.get('design')}/{job_nameid}",
                    os.path.abspath(chip.get('remote', 'key')))

    # Remove dangling 'import' symlinks if necessary.
    for import_link in glob.iglob(job_hash + '/' + top_design + '/**/import*',
                                  recursive=True):
        if os.path.islink(import_link):
            os.remove(import_link)
    # Copy the results into the local build directory, and remove the
    # unzipped directory (including encrypted archives).
    local_dir = chip.get('dir')
    shutil.copytree(job_hash,
                    local_dir,
                    dirs_exist_ok = True)
    shutil.rmtree(job_hash)
