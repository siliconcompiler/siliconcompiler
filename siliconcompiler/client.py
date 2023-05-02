# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import glob
import json
import os
import requests
import shutil
import time
import urllib.parse
import uuid
import tarfile
import tempfile

from siliconcompiler._metadata import default_server
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
def remote_preprocess(chip, steplist):
    '''Helper method to run a local import stage for remote jobs.
    '''

    # Assign a new 'job_hash' to the chip if necessary.
    if 'jobhash' not in chip.status:
        job_hash = uuid.uuid4().hex
        chip.status['jobhash'] = job_hash

    # Fetch a list of 'import' steps, and make sure they're all at the start of the flow.
    flow = chip.get('option', 'flow')
    remote_steplist = steplist.copy()
    entry_steps = chip._get_flowgraph_entry_nodes(flow=flow)
    if any([step not in remote_steplist for step, _ in entry_steps]) or (len(remote_steplist) == 1):
        chip.error('Remote flows must be organized such that the starting task(s) are run before '
                   'all other steps, and at least one other task is included.\n'
                   f'Full steplist: {remote_steplist}\nStarting steps: {entry_steps}',
                   fatal=True)
    # Setup up tools for all local functions
    for local_step, index in entry_steps:
        tool = chip.get('flowgraph', flow, local_step, index, 'tool')
        task = chip._get_task(local_step, index)
        # Setting up tool is optional (step may be a builtin function)
        if not chip._is_builtin(tool, task):
            chip._setup_task(local_step, index)

        # Remove each local step from the list of steps to run on the server side.
        remote_steplist.remove(local_step)

        # Need to override steplist here to make sure check_manifest() doesn't
        # check steps that haven't been setup.
        chip.set('option', 'steplist', local_step)

        # Run the actual import step locally.
        # We can pass in an empty 'status' dictionary, since _runtask() will
        # only look up a step's depedencies in this dictionary, and the first
        # step should have none.
        chip._runtask(local_step, index, {})

    # Collect inputs into a collection directory only for remote runs, since
    # we need to send inputs up to the server.
    chip._collect()

    # Set 'steplist' to only the remote steps, for the future server-side run.
    chip.unset('arg', 'step')
    chip.unset('arg', 'index')
    chip.set('option', 'steplist', remote_steplist, clobber=True)


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
    local_archive = os.path.join(chip._getworkdir(),
                                 'import.tar.gz')
    if os.path.isfile(local_archive):
        os.remove(local_archive)

    # Check the job's progress periodically until it finishes.
    is_busy = True
    while is_busy:
        time.sleep(30)
        try:
            is_busy_info = is_job_busy(chip)
            is_busy = is_busy_info['busy']
            if is_busy:
                if (':' in is_busy_info['message']):
                    msg_lines = is_busy_info['message'].splitlines()
                    cur_step = msg_lines[0][msg_lines[0].find(': ') + 2:]
                    cur_log = '\n'.join(msg_lines[1:])
                    chip.logger.info("Job is still running (%d seconds, step: %s)." % (
                                     int(time.monotonic() - step_start), cur_step))
                    if cur_log:
                        chip.logger.info(f"Tail of current logfile:\n{cur_log}\n")
                else:
                    chip.logger.info("Job is still running (%d seconds, step: unknown)" % (
                                     int(time.monotonic() - step_start)))
        except Exception:
            # Sometimes an exception is raised if the request library cannot
            # reach the server due to a transient network issue.
            # Retrying ensures that jobs don't break off when the connection drops.
            is_busy = True
            chip.logger.info("Unknown network error encountered: retrying.")
    chip.logger.info("Remote job run completed! Fetching results...")


###################################
def request_remote_run(chip):
    '''Helper method to make a web request to start a job stage.
    '''

    # Set the request URL.
    remote_run_url = urllib.parse.urljoin(get_base_url(chip), '/remote_run/')

    # Use authentication if necessary.
    post_params = {
        'chip_cfg': chip.schema.cfg,
        'params': {
            'job_hash': chip.status['jobhash'],
        }
    }
    local_build_dir = chip._getworkdir()
    rcfg = chip.status['remote_cfg']
    if ('username' in rcfg) and ('password' in rcfg) and \
       (rcfg['username']) and (rcfg['password']):
        post_params['params']['username'] = rcfg['username']
        post_params['params']['key'] = rcfg['password']

    # If '-remote_user' and '-remote_key' are not both specified,
    # no authorization is configured; proceed without crypto.
    # If they were specified, these files are now encrypted.

    upload_file = tempfile.TemporaryFile(prefix='sc', suffix='remote.tar.gz')
    with tarfile.open(fileobj=upload_file, mode='w:gz') as tar:
        tar.add(local_build_dir, arcname='')
    # Flush file to ensure everything is written
    upload_file.flush()

    # Print a reminder for public beta runs.
    default_server_name = urllib.parse.urlparse(default_server).hostname
    if default_server_name in remote_run_url:
        default_delay = 5
        chip.logger.warning(f"""Your job will be uploaded to a public server for processing in {default_delay} seconds.
---------------------------------------------------------------------------------------------------
  DISCLAIMER:
  - The open SiliconCompiler remote server is a free service. Please don't abuse it.
  - Submitted designs must be open source. SiliconCompiler is not responsible for any proprietary IP that may be uploaded.
  - Only send one run at a time (or you may be temporarily blocked).
  - Do not send large designs (machines have limited resources).
  - We are currently only returning metrics and renderings of the results. For a full GDS-II layout, please run your design locally.
  - For full TOS, see https://www.siliconcompiler.com/terms-of-service
-------------------------------------------------------------------------------------------------""")
        chip.logger.info(f"Your job's reference ID is: {chip.status['jobhash']}")
        time.sleep(default_delay)

    # Make the actual request, streaming the bulk data as a multipart file.
    # Redirected POST requests are translated to GETs. This is actually
    # part of the HTTP spec, so we need to manually follow the trail.
    redirect_url = remote_run_url
    while redirect_url:
        # Return to start of file
        upload_file.seek(0)
        resp = requests.post(redirect_url,
                             files={'import': upload_file,
                                    'params': json.dumps(post_params)},
                             allow_redirects=False)
        if resp.status_code == 302:
            redirect_url = resp.headers['Location']
        elif resp.status_code >= 400:
            chip.logger.error(resp.json()['message'])
            chip.logger.error('Error starting remote job run; quitting.')
            raise RuntimeError('Remote server returned unrecoverable error code.')
        else:
            chip.logger.info(resp.text)
            break

    upload_file.close()


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
        'job_id': chip.get('option', 'jobname'),
    }

    # Set authentication parameters if necessary.
    rcfg = chip.status['remote_cfg']
    if ('username' in rcfg) and ('password' in rcfg):
        post_params['username'] = rcfg['username']
        post_params['key'] = rcfg['password']

    # Make the request and print its response.
    info = {}
    redirect_url = remote_run_url
    while redirect_url:
        resp = requests.post(redirect_url,
                             data=json.dumps(post_params),
                             allow_redirects=False)
        if resp.status_code == 302:
            redirect_url = resp.headers['Location']
        else:
            info['busy'] = (resp.text != "Job has no running steps.")
            info['message'] = resp.text
            return info


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

       Returns:
       * 0 if no error was encountered.
       * [response code] if the results could not be retrieved.
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
        with open(f'{job_hash}.tar.gz', 'wb') as zipf:
            resp = requests.post(redirect_url,
                                 data=json.dumps(post_params),
                                 allow_redirects=can_redirect,
                                 stream=True)
            if resp.status_code == 302:
                redirect_url = resp.headers['Location']
            elif resp.status_code == 303:
                redirect_url = resp.headers['Location']
                can_redirect = True
            elif resp.status_code == 200:
                shutil.copyfileobj(resp.raw, zipf)
                return 0
            else:
                msg_json = {}
                try:  # (An unexpected server error may not return JSON with a message)
                    msg_json = resp.json()
                    msg = f': {msg_json["message"]}' if 'message' in msg_json else '.'
                except requests.exceptions.JSONDecodeError:
                    msg = '.'
                chip.logger.warning(f'Could not fetch results{msg}')
                return resp.status_code


###################################
def fetch_results(chip):
    '''Helper method to fetch and open job results from a remote compute cluster.
    '''

    # Fetch the remote archive after the last stage.
    results_code = fetch_results_request(chip)

    # Note: the server should eventually delete the results as they age out (~8h), but this will
    # give us a brief period to look at failed results.
    if results_code:
        chip.error(f"Sorry, something went wrong and your job results could not be retrieved. (Response code: {results_code})", fatal=True)

    # Call 'delete_job' to remove the run from the server.
    delete_job(chip)

    # Unzip the results.
    top_design = chip.get('design')
    job_hash = chip.status['jobhash']
    local_dir = chip.get('option', 'builddir')

    # Unauthenticated jobs get a gzip archive, authenticated jobs get nested archives.
    # So we need to extract and delete those.
    with tarfile.open(f'{job_hash}.tar.gz', 'r:gz') as tar:
        tar.extractall()
    # Remove the results archive after it is extracted.
    os.remove(f'{job_hash}.tar.gz')

    # Remove dangling symlinks if necessary.
    for import_link in glob.iglob(job_hash + '/' + top_design + '/**/*',
                                  recursive=True):
        if os.path.islink(import_link):
            os.remove(import_link)
    # Copy the results into the local build directory, and remove the
    # unzipped directory (including encrypted archives).
    utils.copytree(job_hash,
                   local_dir,
                   dirs_exist_ok=True)
    shutil.rmtree(job_hash)

    # Print a message pointing to the results.
    chip.logger.info(f"Your job results are located in: {os.path.abspath(chip._getworkdir())}")
