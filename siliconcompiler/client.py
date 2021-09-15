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

    # Run any local steps if necessary.
    local_steps = []
    for step in chip.getkeys('flowgraph'):
        if not step in chip.get('remote', 'steplist'):
            local_steps.append(step)

    for step in local_steps:
        #setting step to active
        index = "0"
        tool = chip.get('flowgraph', step, index, 'tool')
        searchdir = "siliconcompiler.tools." + tool
        modulename = '.'+tool+'_setup'
        chip.logger.info(f"Setting up tool '{tool}' for remote '{step}' step")

        #Loading all tool modules and checking for errors
        module = importlib.import_module(modulename, package=searchdir)
        setup_tool = getattr(module, "setup_tool")
        setup_tool(chip, step, str(0))

        # Run the actual import step locally.
        manager = multiprocessing.Manager()
        error = manager.dict()
        active = manager.dict()
        chip._runstep(step, str(0), active, error)

    # Set 'steplist' to only the remote steps, for the future server-side run.
    remote_steplist = []
    for step in chip.getkeys('flowgraph'):
        if not step in local_steps:
            remote_steplist.append(step)
    chip.set('steplist', remote_steplist, clobber=True)

    # Upload the archive to the 'import/' server endpoint.
    upload_import_dir(chip)

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
      time.sleep(3)
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
    post_params = {'chip_cfg': chip.cfg}
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        # Read the key and encode it in base64 format.
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['params'] = {
            'username': chip.get('remote', 'user'),
            'key': b64_key,
            'job_hash': chip.get('remote', 'jobhash'),
        }
    else:
        post_params['params'] = {
            'job_hash': chip.get('remote', 'jobhash'),
        }

    # Make the actual request.
    # Redirected POST requests are translated to GETs. This is actually
    # part of the HTTP spec, so we need to manually follow the trail.
    redirect_url = remote_run_url
    while redirect_url:
        resp = requests.post(redirect_url,
                             data=json.dumps(post_params),
                             allow_redirects=False)
        if resp.status_code == 302:
            redirect_url = resp.headers['Location']
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
def upload_import_dir(chip):
    '''Helper method to make an async request uploading the post-import
    files to the remote compute cluster.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/import/'

    # Set common parameters.
    job_nameid = f"{chip.get('jobname')}{chip.get('jobid')}"
    post_params = {
        'job_hash': chip.get('remote', 'jobhash'),
        'job_name': chip.get('jobname'),
        'job_id':   str(chip.get('jobid')),
        'design':   chip.get('design'),
    }

    # Set authentication parameters and encrypt data if necessary.
    # TODO-review: Should an error be thrown if only 'user' or 'key' is present?
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

        # Set up encryption and authentication parameters in the request body.
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['username'] = chip.get('remote', 'user')
        post_params['key'] = b64_key

        # Set up 'temporary cloud host' parameters.
        num_temp_hosts = int(chip.get('remote', 'hosts'))
        if num_temp_hosts > 0:
            post_params['new_hosts'] = num_temp_hosts
            if chip.get('remote', 'ram'):
                post_params['new_host_ram'] = int(chip.get('remote', 'ram'))
            if chip.get('remote', 'threads'):
                post_params['new_host_threads'] = int(chip.get('remote', 'threads'))

    # (If '-remote_user' and '-remote_key' are not both specified,
    #  no authorizaion is configured; proceed without crypto.)
    local_build_dir = stepdir = '/'.join([chip.get('dir'),
                                          chip.get('design'),
                                          job_nameid])
    subprocess.run(['zip',
                    '-r',
                    'import.zip',
                    '.'],
                   cwd=local_build_dir)
    upload_file = os.path.abspath(f'{local_build_dir}/import.zip')

    # Make the 'import' API call and print the response.
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
                chip.logger.error('Error importing project data; quitting.')
                sys.exit(1)
            else:
                chip.logger.info(resp.text)
                return

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
    subprocess.run(['unzip', '%s.zip'%job_hash])
    # Remove the results archive after it is extracted.
    os.remove('%s.zip'%job_hash)

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
