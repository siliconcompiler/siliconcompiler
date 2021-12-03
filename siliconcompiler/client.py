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
import urllib.parse
import uuid

from siliconcompiler.crypto import *
from siliconcompiler import utils

###################################
def get_base_url(chip):
    '''Helper method to get the root URL for API calls, given a Chip object.
    '''

    rcfg = chip.status['remote_cfg']
    remote_host = rcfg['address']
    if 'port' in rcfg:
        remote_port = rcfg['port']
    else:
        remote_port = 443
    remote_host += ':' + str(remote_port)
    if remote_host.startswith('http'):
        remote_protocol = ''
    else:
        remote_protocol = 'https://' if str(remote_port) == '443' else 'http://'
    return remote_protocol + remote_host

###################################
def remote_preprocess(chip):
    '''Helper method to run a local import stage for remote jobs.
    '''

    # Assign a new 'job_hash' to the chip if necessary.
    if not 'jobhash' in chip.status:
        job_hash = uuid.uuid4().hex
        chip.status['jobhash'] = job_hash

    manager = multiprocessing.Manager()
    error = manager.dict()
    active = manager.dict()

    # Setup up tools for all local functions
    remote_steplist = chip.getkeys('flowgraph')
    local_step = remote_steplist[0]
    indexlist = chip.getkeys('flowgraph', local_step)
    for index in indexlist:
        tool = chip.get('flowgraph', local_step, index, 'tool')
        # Setting up tool is optional (step may be a builtin function)
        if tool:
            chip.set('arg', 'step', local_step)
            chip.set('arg', 'index', index)
            func = chip.find_function(tool, 'tool', 'setup_tool')
            func(chip)
            # Run the actual import step locally.
            chip._runtask(local_step, index, active, error)

    # Set 'steplist' to only the remote steps, for the future server-side run.
    remote_steplist = remote_steplist[1:]
    chip.set('steplist', remote_steplist, clobber=True)

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

    # Remove the local 'import.tar.gz' archive.
    local_archive = stepdir = os.path.join(chip.get('dir'),
                                           chip.get('design'),
                                           chip.get('jobname'),
                                           'import.tar.gz')
    if os.path.isfile(local_archive):
        os.remove(local_archive)

    # Check the job's progress periodically until it finishes.
    is_busy = True
    while is_busy:
      chip.logger.info("Job is still running. (%d seconds)"%(
                       int(time.monotonic() - step_start)))
      time.sleep(30)
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
    remote_run_url = urllib.parse.urljoin(get_base_url(chip), '/remote_run/')

    # Use authentication if necessary.
    job_nameid = f"{chip.get('jobname')}"
    post_params = {
        'chip_cfg': chip.cfg,
        'params': {
            'job_hash': chip.status['jobhash'],
        }
    }
    local_build_dir = stepdir = os.path.join(chip.get('dir'),
                                             chip.get('design'),
                                             job_nameid)
    rcfg = chip.status['remote_cfg']
    if ('username' in rcfg) and ('password' in rcfg):
        post_params['params']['username'] = rcfg['username']
        post_params['params']['key'] = rcfg['password']

    # If '-remote_user' and '-remote_key' are not both specified,
    # no authorizaion is configured; proceed without crypto.
    # If they were specified, these files are now encrypted.
    subprocess.run(['tar',
                    '-czf',
                    'import.tar.gz',
                    '--exclude',
                    'import.tar.gz',
                    '.'],
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   cwd=local_build_dir)
    upload_file = os.path.abspath(os.path.join(local_build_dir, 'import.tar.gz'))

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
                chip.logger.error(resp.json()['message'])
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
    remote_run_url = urllib.parse.urljoin(get_base_url(chip), '/check_progress/')

    # Set common parameters.
    post_params = {
        'job_hash': chip.status['jobhash'],
        'job_id': chip.get('jobname'),
    }

    # Set authentication parameters if necessary.
    rcfg = chip.status['remote_cfg']
    if ('username' in rcfg) and ('password' in rcfg):
        post_params['username'] = rcfg['username']
        post_params['key'] = rcfg['password']

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
    remote_run_url = urllib.parse.urljoin(get_base_url(chip), '/delete_job/')

    # Set common parameter.
    post_params = {
        'job_hash': chip.status['jobhash'],
    }

    # Set authentication parameters if necessary.
    rcfg = chip.status['remote_cfg']
    if ('username' in rcfg) and ('password' in rcfg):
        post_params['username'] = rcfg['username']
        post_params['key'] = rcfg['password']

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
    job_hash = chip.status['jobhash']
    remote_run_url = urllib.parse.urljoin(get_base_url(chip), '/get_results/' + job_hash + '.tar.gz')

    # Set authentication parameters if necessary.
    rcfg = chip.status['remote_cfg']
    if ('username' in rcfg) and ('password' in rcfg):
        post_params = {
            'username': rcfg['username'],
            'key': rcfg['password'],
        }
    else:
        post_params = {}

    # Make the web request, and stream the results archive in chunks.
    redirect_url = remote_run_url
    can_redirect = False
    while redirect_url:
        with open('%s.tar.gz'%job_hash, 'wb') as zipf:
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

    # Call 'delete_job' to remove the run from the server.
    delete_job(chip)

    # Unzip the results.
    top_design = chip.get('design')
    job_hash = chip.status['jobhash']
    job_nameid = f"{chip.get('jobname')}"
    local_dir = chip.get('dir')

    # Authenticated jobs get a zip file full of other zip files.
    # So we need to extract and delete those.
    subprocess.run(['tar', '-xzf', f'{job_hash}.tar.gz'])
    # Remove the results archive after it is extracted.
    os.remove(f'{job_hash}.tar.gz')

    # Remove dangling 'import' symlinks if necessary.
    for import_link in glob.iglob(job_hash + '/' + top_design + '/**/import*',
                                  recursive=True):
        if os.path.islink(import_link):
            os.remove(import_link)
    # Copy the results into the local build directory, and remove the
    # unzipped directory (including encrypted archives).
    utils.copytree(job_hash,
                   local_dir,
                   dirs_exist_ok = True)
    shutil.rmtree(job_hash)
