# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import glob
import json
import os
import requests
import shutil
import time
import urllib.parse
import tarfile
import tempfile
import multiprocessing

from siliconcompiler import utils, SiliconCompilerError
from siliconcompiler._metadata import default_server
from siliconcompiler.schema import Schema
from siliconcompiler.utils import default_credentials_file


# Client / server timeout
__timeout = 10

# Multiprocessing interface.
multiprocessor = multiprocessing.get_context('spawn')

__tos_str = '''Please review the SiliconCompiler cloud beta's terms of service:

https://www.siliconcompiler.com/terms-of-service

In particular, please ensure that you have the right to distribute any IP
which is contained in designs that you upload to the service. This public
service, provided by SiliconCompiler, is not intended to process proprietary IP.
'''


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
def __post(chip, url, post_action, success_action, error_action=None):
    '''
    Helper function to handle the post request
    '''
    redirect_url = urllib.parse.urljoin(get_base_url(chip), url)

    timeouts = 0
    while redirect_url:
        try:
            resp = post_action(redirect_url)
        except requests.Timeout:
            timeouts += 1
            if timeouts > 10:
                chip.error('Server communications timed out', fatal=True)
            time.sleep(10)
            continue
        except Exception as e:
            chip.error(f'Server communications error: {e}', fatal=True)

        code = resp.status_code
        if 200 <= code and code < 300:
            return success_action(resp)

        try:
            msg_json = resp.json()
            if 'message' in msg_json:
                msg = msg_json['message']
            else:
                msg = resp.text
        except requests.JSONDecodeError:
            msg = resp.text

        if 300 <= code and code < 400:
            if 'Location' in resp.headers:
                redirect_url = resp.headers['Location']
                continue

        if error_action:
            return error_action(code, msg)
        else:
            chip.error(f'Server responded with {code}: {msg}', fatal=True)


###################################
def __build_post_params(chip, job_name=None, job_hash=None):
    '''
    Helper function to build the params for the post request
    '''
    # Use authentication if necessary.
    post_params = {}

    if job_hash:
        post_params['job_hash'] = job_hash

    if job_name:
        post_params['job_id'] = job_name

    if 'remote_cfg' in chip.status:
        rcfg = chip.status['remote_cfg']
        if ('username' in rcfg) and ('password' in rcfg) and \
           (rcfg['username']) and (rcfg['password']):
            post_params['username'] = rcfg['username']
            post_params['key'] = rcfg['password']

    return post_params


###################################
def _remote_preprocess(chip, remote_nodelist):
    '''
    Helper method to run a local import stage for remote jobs.
    '''
    preset_step = chip.get('arg', 'step')
    preset_index = chip.get('arg', 'index')

    # Fetch a list of 'import' steps, and make sure they're all at the start of the flow.
    flow = chip.get('option', 'flow')
    entry_nodes = chip._get_flowgraph_entry_nodes(flow)
    if any([node not in remote_nodelist for node in entry_nodes]) or (len(remote_nodelist) == 1):
        chip.error('Remote flows must be organized such that the starting task(s) are run before '
                   'all other steps, and at least one other task is included.\n'
                   f'Full nodelist: {remote_nodelist}\nStarting nodes: {entry_nodes}',
                   fatal=True)
    # Setup up tools for all local functions
    for local_step, index in entry_nodes:
        tool = chip.get('flowgraph', flow, local_step, index, 'tool')
        task = chip._get_task(local_step, index)
        # Setting up tool is optional (step may be a builtin function)
        if not chip._is_builtin(tool, task):
            chip._setup_node(local_step, index)

        # Need to set step/index to only run this node locally
        chip.set('arg', 'step', local_step)
        chip.set('arg', 'index', index)

        if not chip.get('option', 'resume'):

            # Run the actual import step locally with multiprocess as _runtask must
            # be run in a separate thread.
            # We can pass in an empty 'status' dictionary, since _runtask() will
            # only look up a step's dependencies in this dictionary, and the first
            # step should have none.
            run_task = multiprocessor.Process(target=chip._runtask,
                                              args=(flow, local_step, index, {}))
            run_task.start()
            run_task.join()
            if run_task.exitcode != 0:
                # A 'None' or nonzero value indicates that the Process target failed.
                ftask = f'{local_step}{index}'
                chip.error(f"Could not start remote job: local setup task {ftask} failed.",
                           fatal=True)

    # Collect inputs into a collection directory only for remote runs, since
    # we need to send inputs up to the server.
    chip._collect()

    # Recover step/index
    chip.set('arg', 'step', preset_step)
    chip.set('arg', 'index', preset_index)


###################################
def _log_truncated_stats(chip, status, nodes_with_status, nodes_to_print):
    '''
    Helper method to log truncated information about flowgraph nodes
    with a given status, on a single line.
    Used to print info about all statuses besides 'running'.
    '''

    num_nodes = len(nodes_with_status)
    if num_nodes > 0:
        nodes_log = f'  {status.title()} ({num_nodes}): '
        log_nodes = []
        for i in range(min(nodes_to_print, num_nodes)):
            log_nodes.append(nodes_with_status[i][0])
        if num_nodes > nodes_to_print:
            log_nodes.append('...')
        nodes_log += ', '.join(log_nodes)
        chip.logger.info(nodes_log)


###################################
def _process_progress_info(chip, progress_info, nodes_to_print=3):
    '''
    Helper method to log information about a remote run's progress,
    based on information returned from a 'check_progress/' call.
    '''

    try:
        # Decode response JSON, if possible.
        job_info = json.loads(progress_info['message'])
        # Retrieve total elapsed time, if included in the response.
        total_elapsed = ''
        if 'elapsed_time' in job_info:
            total_elapsed = f' (runtime: {job_info["elapsed_time"]})'

        # Sort and store info about the job's progress.
        completed = []
        chip.logger.info(f"Job is still running{total_elapsed}. Status:")
        nodes_to_log = {'completed': [], 'failed': [], 'timeout': [],
                        'running': [], 'queued': [], 'pending': []}
        for node, node_info in job_info.items():
            status = node_info['status']
            nodes_to_log[status].append((node, node_info))
            if (status == 'completed'):
                completed.append(node)

        # Log information about the job's progress.
        # To avoid clutter, only log up to N completed/pending nodes, on a single line.
        # Completed, failed, and timed-out flowgraph nodes:
        for stat in ['completed', 'failed', 'timeout']:
            _log_truncated_stats(chip, stat, nodes_to_log[stat], nodes_to_print)
        # Running / in-progress flowgraph nodes should all be printed:
        num_running = len(nodes_to_log['running'])
        if num_running > 0:
            chip.logger.info(f'  Running ({num_running}):')
            for node_tuple in nodes_to_log['running']:
                node = node_tuple[0]
                node_info = node_tuple[1]
                running_log = f"    {node}"
                if 'elapsed_time' in node_info:
                    running_log += f" ({node_info['elapsed_time']})"
                chip.logger.info(running_log)
        # Queued and pending flowgraph nodes:
        for stat in ['queued', 'pending']:
            _log_truncated_stats(chip, stat, nodes_to_log[stat], nodes_to_print)
    except json.JSONDecodeError:
        # TODO: Remove fallback once all servers are updated to return JSON.
        if (':' in progress_info['message']):
            msg_lines = progress_info['message'].splitlines()
            cur_step = msg_lines[0][msg_lines[0].find(': ') + 2:]
            cur_log = '\n'.join(msg_lines[1:])
            chip.logger.info("Job is still running (step: %s)." % (
                             cur_step))
            if cur_log:
                chip.logger.info(f"Tail of current logfile:\n{cur_log}\n")
        else:
            chip.logger.info("Job is still running (step: unknown)")

    return completed


def _load_remote_config(chip):
    '''
    Load the remote storage config into the status dictionary.
    '''
    if chip.get('option', 'credentials'):
        # Use the provided remote credentials file.
        cfg_file = os.path.abspath(chip.get('option', 'credentials'))

        if not os.path.isfile(cfg_file):
            # Check if it's a file since its been requested by the user
            chip.error(f'Unable to find the credentials file: {cfg_file}', fatal=True)
    else:
        # Use the default config file path.
        cfg_file = utils.default_credentials_file()

    cfg_dir = os.path.dirname(cfg_file)
    if os.path.isdir(cfg_dir) and os.path.isfile(cfg_file):
        chip.logger.info(f'Using credentials: {cfg_file}')
        with open(cfg_file, 'r') as cfgf:
            chip.status['remote_cfg'] = json.loads(cfgf.read())
    else:
        chip.logger.warning('Could not find remote server configuration: '
                            f'defaulting to {default_server}')
        chip.status['remote_cfg'] = {
            "address": default_server
        }
    if ('address' not in chip.status['remote_cfg']):
        chip.error('Improperly formatted remote server configuration - '
                   'please run "sc-configure" and enter your server address and '
                   'credentials.', fatal=True)


def remote_process(chip):
    '''
    Dispatch the Chip to a remote server for processing.
    '''
    _load_remote_config(chip)
    should_resume = chip.get('option', 'resume')
    remote_resume = should_resume and chip.get('record', 'remoteid')

    # Pre-process: Run an starting nodes locally, and upload the
    # in-progress build directory to the remote server.
    # Data is encrypted if user / key were specified.
    # run remote process
    if should_resume:
        chip.unset('arg', 'step')
        chip.unset('arg', 'index')
    elif chip.get('arg', 'step'):
        chip.error('Cannot pass "-step" parameter into remote flow.', fatal=True)
    # Only run the pre-process step if the job doesn't already have a remote ID.
    if not remote_resume:
        _remote_preprocess(chip, chip.nodes_to_execute(chip.get('option', 'flow')))

    # Run the job on the remote server, and wait for it to finish.
    # Set logger to indicate remote run
    chip._init_logger(step='remote', index='0', in_run=True)
    _remote_run(chip)

    # Restore logger
    chip._init_logger(in_run=True)


###################################
def _remote_run(chip):
    '''
    Helper method to run a job stage on a remote compute cluster.
    Note that files will not be copied to the remote stage; typically
    the source files will be copied into the cluster's storage before
    calling this method.
    If the "-remote" parameter was not passed in, this method
    will print a warning and do nothing.
    This method assumes that the given stage should not be skipped,
    because it is called from within the `Chip.run(...)` method.

    '''

    # Ask the remote server to start processing the requested step.
    _request_remote_run(chip)

    # Remove the local 'import.tar.gz' archive.
    local_archive = os.path.join(chip._getworkdir(),
                                 'import.tar.gz')
    if os.path.isfile(local_archive):
        os.remove(local_archive)

    # Run the main 'check_progress' loop to monitor job status until it finishes.
    remote_run_loop(chip)


###################################
def remote_run_loop(chip):
    # Wrapper to allow for capturing of Ctrl+C
    try:
        __remote_run_loop(chip)
    except KeyboardInterrupt:
        entry_step, entry_index = \
            chip._get_flowgraph_entry_nodes(chip.get('option', 'flow'))[0]
        entry_manifest = os.path.join(chip._getworkdir(step=entry_step, index=entry_index),
                                      'outputs',
                                      f'{chip.design}.pkg.json')
        reconnect_cmd = f'sc-remote -cfg {entry_manifest} -reconnect'
        cancel_cmd = f'sc-remote -cfg {entry_manifest} -cancel'
        chip.logger.info('Disconnecting from remote job')
        chip.logger.info(f'To reconnect to this job use: {reconnect_cmd}')
        chip.logger.info(f'To cancel this job use: {cancel_cmd}')
        raise SiliconCompilerError('Job canceled by user keyboard interrupt')


###################################
def __remote_run_loop(chip):
    # Check the job's progress periodically until it finishes.
    is_busy = True
    all_nodes = []
    for (step, index) in chip.nodes_to_execute():
        all_nodes.append(f'{step}{index}')
    completed = []
    result_procs = []
    while is_busy:
        time.sleep(30)
        new_completed, is_busy = check_progress(chip)
        nodes_to_fetch = []
        for node in new_completed:
            if node not in completed:
                nodes_to_fetch.append(node)
                completed.append(node)
        if nodes_to_fetch:
            chip.logger.info('  Fetching completed results:')
            for node in nodes_to_fetch:
                node_proc = multiprocessor.Process(target=fetch_results,
                                                   args=(chip, node))
                node_proc.start()
                result_procs.append(node_proc)
                chip.logger.info(f'    {node}')

    # Done: try to fetch any node results which still haven't been retrieved.
    chip.logger.info('Remote job completed! Retrieving final results...')
    for node in all_nodes:
        if node not in completed:
            node_proc = multiprocessor.Process(target=fetch_results,
                                               args=(chip, node))
            node_proc.start()
            result_procs.append(node_proc)
    # Make sure all results are fetched before letting the client issue
    # a deletion request.
    for proc in result_procs:
        proc.join()

    # Un-set the 'remote' option to avoid from/to-based summary/show errors
    chip.unset('option', 'remote')


###################################
def check_progress(chip):
    try:
        is_busy_info = is_job_busy(chip)
        is_busy = is_busy_info['busy']
        completed = []
        if is_busy:
            completed = _process_progress_info(chip,
                                               is_busy_info)
        return completed, is_busy
    except Exception:
        # Sometimes an exception is raised if the request library cannot
        # reach the server due to a transient network issue.
        # Retrying ensures that jobs don't break off when the connection drops.
        chip.logger.info("Unknown network error encountered: retrying.")
        return [], True


###################################
def _update_entry_manifests(chip):
    '''
    Helper method to update locally-run manifests to include remote job ID.
    '''

    flow = chip.get('option', 'flow')
    jobid = chip.get('record', 'remoteid')
    design = chip.get('design')

    entry_nodes = chip._get_flowgraph_entry_nodes(flow)
    for step, index in entry_nodes:
        manifest_path = os.path.join(chip._getworkdir(step=step, index=index),
                                     'outputs',
                                     f'{design}.pkg.json')
        tmp_schema = Schema(manifest=manifest_path)
        tmp_schema.set('record', 'remoteid', jobid)
        tmp_schema.set('option', 'from', chip.get('option', 'from'))
        tmp_schema.set('option', 'to', chip.get('option', 'to'))
        with open(manifest_path, 'w') as new_manifest:
            tmp_schema.write_json(new_manifest)


###################################
def _request_remote_run(chip):
    '''
    Helper method to make a web request to start a job stage.
    '''

    remote_resume = (chip.get('option', 'resume') and chip.get('record', 'remoteid'))
    # Only package and upload the entry steps if starting a new job.
    if not remote_resume:
        upload_file = tempfile.TemporaryFile(prefix='sc', suffix='remote.tar.gz')
        with tarfile.open(fileobj=upload_file, mode='w:gz') as tar:
            tar.add(chip._getworkdir(), arcname='')
        # Flush file to ensure everything is written
        upload_file.flush()

    # Print a reminder for public beta runs.
    default_server_name = urllib.parse.urlparse(default_server).hostname
    if default_server_name in get_base_url(chip):
        upload_delay = 5
        chip.logger.info(f"Your job will be uploaded to a public server in {upload_delay} seconds.")
        chip.logger.warning("""
-----------------------------------------------------------------------------------------------
  DISCLAIMER:
  - The open SiliconCompiler remote server is a free service. Please don't abuse it.
  - Submitted designs must be open source. SiliconCompiler is not responsible for any
    proprietary IP that may be uploaded.
  - Only send one run at a time (or you may be temporarily blocked).
  - Do not send large designs (machines have limited resources).
  - Nontrivial designs may take some time to run. (machines have limited resources).
  - For full TOS, see https://www.siliconcompiler.com/terms-of-service
-----------------------------------------------------------------------------------------------""")
        time.sleep(upload_delay)

    # Make the actual request, streaming the bulk data as a multipart file.
    # Redirected POST requests are translated to GETs. This is actually
    # part of the HTTP spec, so we need to manually follow the trail.
    post_params = {
        'chip_cfg': chip.schema.cfg,
        'params': __build_post_params(chip,
                                      job_hash=chip.get('record', 'remoteid'))
    }

    post_files = {'params': json.dumps(post_params)}
    if not remote_resume:
        post_files['import'] = upload_file
        upload_file.seek(0)

    def post_action(url):
        return requests.post(url,
                             files=post_files,
                             timeout=__timeout)

    def success_action(resp):
        return resp.json()

    resp = __post(chip, '/remote_run/', post_action, success_action)
    if not remote_resume:
        upload_file.close()

    if 'message' in resp and resp['message']:
        chip.logger.info(resp['message'])
    chip.set('record', 'remoteid', resp['job_hash'])
    _update_entry_manifests(chip)
    chip.logger.info(f"Your job's reference ID is: {resp['job_hash']}")


###################################
def is_job_busy(chip):
    '''
    Helper method to make an async request asking the remote server
    whether a job is busy, or ready to accept a new step.
    Returns True if the job is busy, False if not.
    '''

    # Make the request and print its response.
    def post_action(url):
        params = __build_post_params(chip,
                                     job_hash=chip.get('record', 'remoteid'),
                                     job_name=chip.get('option', 'jobname'))
        return requests.post(url,
                             data=json.dumps(params),
                             timeout=__timeout)

    def error_action(code, msg):
        return {
            'busy': True,
            'message': ''
        }

    def success_action(resp):
        # Determine job completion based on response message, or preferably JSON parameter.
        # TODO: Only accept JSON response's "status" field once server changes are rolled out.
        is_busy = ("Job has no running steps." not in resp.text)
        try:
            json_response = json.loads(resp.text)
            if ('status' in json_response) and (json_response['status'] == 'completed'):
                is_busy = False
            elif ('status' in json_response) and (json_response['status'] == 'canceled'):
                chip.logger.info('Job was canceled.')
                is_busy = False
        except requests.JSONDecodeError:
            # Message may have been text-formatted.
            pass
        info = {
            'busy': is_busy,
            'message': resp.text
        }
        return info

    info = __post(chip,
                  '/check_progress/',
                  post_action,
                  success_action,
                  error_action=error_action)

    if not info:
        info = {
            'busy': True,
            'message': ''
        }
    return info


###################################
def cancel_job(chip):
    '''
    Helper method to request that the server cancel an ongoing job.
    '''

    def post_action(url):
        return requests.post(url,
                             data=json.dumps(__build_post_params(
                                 chip,
                                 job_hash=chip.get('record', 'remoteid'))),
                             timeout=__timeout)

    def success_action(resp):
        return json.loads(resp.text)

    return __post(chip, '/cancel_job/', post_action, success_action)


###################################
def delete_job(chip):
    '''
    Helper method to delete a job from shared remote storage.
    '''

    def post_action(url):
        return requests.post(url,
                             data=json.dumps(__build_post_params(
                                 chip,
                                 job_hash=chip.get('record', 'remoteid'))),
                             timeout=__timeout)

    def success_action(resp):
        return resp.text

    return __post(chip, '/delete_job/', post_action, success_action)


###################################
def fetch_results_request(chip, node, results_path):
    '''
    Helper method to fetch job results from a remote compute cluster.
    Optional 'node' argument fetches results for only the specified
    flowgraph node (e.g. "floorplan0")

       Returns:
       * 0 if no error was encountered.
       * [response code] if the results could not be retrieved.
    '''

    # Set the request URL.
    job_hash = chip.get('record', 'remoteid')

    # Fetch results archive.
    with open(results_path, 'wb') as zipf:
        def post_action(url):
            post_params = __build_post_params(chip)
            if node:
                post_params['node'] = node
            return requests.post(url,
                                 data=json.dumps(post_params),
                                 stream=True,
                                 timeout=__timeout)

        def success_action(resp):
            shutil.copyfileobj(resp.raw, zipf)
            return 0

        def error_action(code, msg):
            # Results are fetched in parallel, and a failure in one node
            # does not necessarily mean that the whole job failed.
            chip.logger.warning(f'Could not fetch results for node: {node}')
            return 404

        return __post(chip,
                      f'/get_results/{job_hash}.tar.gz',
                      post_action,
                      success_action,
                      error_action=error_action)


###################################
def fetch_results(chip, node, results_path=None):
    '''
    Helper method to fetch and open job results from a remote compute cluster.
    Optional 'node' argument fetches results for only the specified
    flowgraph node (e.g. "floorplan0")
    '''

    # Collect local values.
    top_design = chip.get('design')
    job_hash = chip.get('record', 'remoteid')
    local_dir = chip.get('option', 'builddir')

    # Set default results archive path if necessary, and fetch it.
    if not results_path:
        results_path = f'{job_hash}{node}.tar.gz'
    results_code = fetch_results_request(chip, node, results_path)

    # Note: the server should eventually delete the results as they age out (~8h), but this will
    # give us a brief period to look at failed results.
    if not node and results_code:
        chip.error("Sorry, something went wrong and your job results could not be retrieved. "
                   f"(Response code: {results_code})", fatal=True)
    if node and results_code:
        # nothing was received no need to unzip
        return

    # Unzip the results.
    # Unauthenticated jobs get a gzip archive, authenticated jobs get nested archives.
    # So we need to extract and delete those.
    # Archive contents: server-side build directory. Format:
    # [job_hash]/[design]/[job_name]/[step]/[index]/...
    try:
        with tarfile.open(results_path, 'r:gz') as tar:
            tar.extractall(path=(node if node else ''))
    except tarfile.TarError as e:
        chip.logger.error(f'Failed to extract data from {results_path}: {e}')
        return
    finally:
        # Remove the results archive after it is extracted.
        os.remove(results_path)

    # Remove dangling symlinks if necessary.
    for import_link in glob.iglob(job_hash + '/' + top_design + '/**/*',
                                  recursive=True):
        if os.path.islink(import_link):
            os.remove(import_link)
    # Copy the results into the local build directory, and remove the
    # unzipped directory.
    basedir = os.path.join(node, job_hash) if node else job_hash
    utils.copytree(basedir,
                   local_dir,
                   dirs_exist_ok=True)
    shutil.rmtree(node if node else job_hash)

    # Print a message pointing to the results.
    if not node:
        chip.logger.info(f"Your job results are located in: {os.path.abspath(chip._getworkdir())}")


###################################
def remote_ping(chip):
    '''
    Helper method to call check_server on server
    '''

    # Make the request and print its response.
    def post_action(url):
        return requests.post(url,
                             data=json.dumps(__build_post_params(chip)),
                             timeout=__timeout)

    def success_action(resp):
        return resp.json()

    response_info = __post(chip, '/check_server/', post_action, success_action)
    if not response_info:
        raise ValueError('Server response is not valid.')

    # Print user info if applicable.
    # TODO: `if 'username' in remote_cfg:` instead?
    if 'user_info' in response_info:
        user_info = response_info['user_info']
        if ('compute_time' not in user_info) or \
           ('bandwidth_kb' not in user_info):
            chip.logger.info('Error fetching user information from the remote server.')
            raise ValueError(f'Server response is not valid or missing fields: {user_info}')

        if 'remote_cfg' in chip.status:
            remote_cfg = chip.status['remote_cfg']
            # Print the user's account info, and return.
            chip.logger.info(f'User {remote_cfg["username"]}:')
        time_remaining = user_info["compute_time"] / 60.0
        bandwidth_remaining = user_info["bandwidth_kb"]
        chip.logger.info(f'  Remaining compute time: {(time_remaining):.2f} minutes')
        chip.logger.info(f'  Remaining results bandwidth: {bandwidth_remaining} KiB')

    # Print status value.
    server_status = response_info['status']
    chip.logger.info(f'Server status: {server_status}')
    if server_status != 'ready':
        chip.logger.warning('  Status is not "ready", server cannot accept new jobs.')

    # Print server-side version info.
    version_info = response_info['versions']
    version_suffix = ' version'
    max_name_string_len = max([len(s) for s in version_info.keys()]) + len(version_suffix)
    chip.logger.info('Server software versions:')
    for name, version in version_info.items():
        print_name = f'{name}{version_suffix}'
        chip.logger.info(f'  {print_name: <{max_name_string_len}}: {version}')

    # Print terms-of-service message, if the server provides one.
    if 'terms' in response_info and response_info['terms']:
        chip.logger.info('Terms of Service info for this server:')
        chip.logger.info(response_info['terms'])

    # Return the response info in case the caller wants to inspect it.
    return response_info


def configure(chip, server=None, port=None, username=None, password=None):

    def confirm_dialog(message):
        confirmed = False
        while not confirmed:
            oin = input(f'{message} y/N: ')
            if (not oin) or (oin == 'n') or (oin == 'N'):
                return False
            elif (oin == 'y') or (oin == 'Y'):
                return True
        return False

    default_server_name = urllib.parse.urlparse(default_server).hostname

    # Find the config file/directory path.
    cfg_file = chip.get('option', 'credentials')
    if not cfg_file:
        cfg_file = default_credentials_file()
    cfg_dir = os.path.dirname(cfg_file)

    # Create directory if it doesn't exist.
    if cfg_dir and not os.path.isdir(cfg_dir):
        os.makedirs(cfg_dir, exist_ok=True)

    # If an existing config file exists, prompt the user to overwrite it.
    if os.path.isfile(cfg_file):
        if not confirm_dialog('Overwrite existing remote configuration?'):
            return

    config = {}

    # If a command-line argument is passed in, use that as a public server address.
    if server:
        srv_addr = server
        chip.logger.info(f'Creating remote configuration file for server: {srv_addr}')
    else:
        # If no arguments were passed in, interactively request credentials from the user.
        srv_addr = input('Remote server address (leave blank to use default server):\n')
        srv_addr = srv_addr.replace(" ", "")

    if not srv_addr:
        srv_addr = default_server
        chip.logger.info(f'Using {srv_addr} as server')

    server = urllib.parse.urlparse(srv_addr)
    has_scheme = True
    if not server.hostname:
        # fake add a scheme to the url
        has_scheme = False
        server = urllib.parse.urlparse('https://' + srv_addr)
    if not server.hostname:
        raise ValueError(f'Invalid address provided: {srv_addr}')

    if has_scheme:
        config['address'] = f'{server.scheme}://{server.hostname}'
    else:
        config['address'] = server.hostname

    public_server = default_server_name in srv_addr
    if public_server and not confirm_dialog(__tos_str):
        return

    if server.port is not None:
        config['port'] = server.port

    if not public_server:
        if username is None:
            username = server.username
            if username is None:
                username = input('Remote username (leave blank for no username):\n')
                username = username.replace(" ", "")
        if password is None:
            password = server.password
            if password is None:
                password = input('Remote password (leave blank for no password):\n')
                password = password.replace(" ", "")

        if username:
            config['username'] = username
        if password:
            config['password'] = password

    # Save the values to the target config file in JSON format.
    with open(cfg_file, 'w') as f:
        f.write(json.dumps(config, indent=4))

    # Let the user know that we finished successfully.
    chip.logger.info(f'Remote configuration saved to: {cfg_file}')
