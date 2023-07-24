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
import multiprocessing

from siliconcompiler._metadata import default_server
from siliconcompiler import utils


# Client / server timeout
__timeout = 10


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
def remote_preprocess(chip, steplist):
    '''
    Helper method to run a local import stage for remote jobs.
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
    multiprocessor = multiprocessing.get_context('spawn')
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

        # Run the actual import step locally with multiprocess as _runtask must
        # be run in a seperate thread.
        # We can pass in an empty 'status' dictionary, since _runtask() will
        # only look up a step's depedencies in this dictionary, and the first
        # step should have none.
        run_task = multiprocessor.Process(target=chip._runtask,
                                          args=(local_step, index, {}))
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

    # Set 'steplist' to only the remote steps, for the future server-side run.
    chip.unset('arg', 'step')
    chip.unset('arg', 'index')
    chip.set('option', 'steplist', remote_steplist, clobber=True)


###################################
def log_progress_info(chip, progress_info, node='', nodes_to_print=3):
    '''
    Helper method to log information about a remote run's progress,
    based on information returned from a 'check_progress/' call.
    '''

    try:
        # Decode response JSON, if possible.
        job_info = json.loads(is_busy_info['message'])
        # Retrieve total elapsed time, if included in the response.
        total_elapsed = ''
        if 'elapsed_time' in job_info:
            total_elapsed = f' (runtime: {job_info["elapsed_time"]})'

        # Sort and store info about the job's progress.
        chip.logger.info(f"Job is still running{total_elapsed}. Status:")
        nodes_to_fetch = []
        nodes_to_log = {'completed': [], 'running': [], 'pending': []}
        for node, node_info in job_info.items():
            status = node_info['status']
            nodes_to_log[status].append((node, node_info))
            if (status == 'completed') and \
               (node not in completed):
                completed.append(node)
                nodes_to_fetch.append(node)

        # Log information about the job's progress.
        # To avoid clutter, only log up to N completed/pending nodes, on a single line.
        # Completed flowgraph nodes:
        num_completed = len(nodes_to_log["completed"])
        if num_completed > 0:
            completed_log = f'  Completed ({num_completed}): '
            completed_nodes = []
            for i in range(min(nodes_to_print, num_completed)):
                completed_nodes.append(nodes_to_log['completed'][i][0])
            if num_completed > nodes_to_print:
                completed_nodes.append('...')
            completed_log += ', '.join(completed_nodes)
            chip.logger.info(completed_log)
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
        # Pending flowgraph nodes:
        num_pending = len(nodes_to_log['pending'])
        if num_pending > 0:
            pending_log = f'  Pending ({num_pending}): '
            pending_nodes = []
            for i in range(min(nodes_to_print, num_pending)):
                pending_nodes.append(nodes_to_log['pending'][i][0])
            if num_pending > nodes_to_print:
                pending_nodes.append('...')
            pending_log += ', '.join(pending_nodes)
            chip.logger.info(pending_log)

        # Kick off result downloads for newly-completed nodes.
        if nodes_to_fetch:
            chip.logger.info('  Fetching newly-completed results:')
            for node in nodes_to_fetch:
                node_proc = multiprocessor.Process(target=fetch_results,
                                                   args=(chip, node))
                node_proc.start()
                result_procs.append(node_proc)
                chip.logger.info(f'    {node}')
    except json.JSONDecodeError:
        # TODO: Remove fallback once all servers are updated to return JSON.
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


###################################
def remote_run(chip):
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
    all_nodes = []
    result_procs = []
    for step in chip.get('option', 'steplist'):
        for index in chip.getkeys('flowgraph', chip.get('option', 'flow'), step):
            all_nodes.append(f'{step}{index}')
    completed = []
    multiprocessor = multiprocessing.get_context('spawn')
    while is_busy:
        time.sleep(30)
        try:
            is_busy_info = is_job_busy(chip)
            is_busy = is_busy_info['busy']
            if is_busy:
                log_progress_info(chip, is_busy_info, node)
            else:
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
        except Exception:
            # Sometimes an exception is raised if the request library cannot
            # reach the server due to a transient network issue.
            # Retrying ensures that jobs don't break off when the connection drops.
            is_busy = True
            chip.logger.info("Unknown network error encountered: retrying.")


###################################
def request_remote_run(chip):
    '''
    Helper method to make a web request to start a job stage.
    '''

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
  - We are currently only returning metrics and renderings of the results. For a full GDS-II
    layout, please run your design locally.
  - For full TOS, see https://www.siliconcompiler.com/terms-of-service
-----------------------------------------------------------------------------------------------""")
        time.sleep(upload_delay)

    chip.logger.info(f"Your job's reference ID is: {chip.status['jobhash']}")

    # Make the actual request, streaming the bulk data as a multipart file.
    # Redirected POST requests are translated to GETs. This is actually
    # part of the HTTP spec, so we need to manually follow the trail.
    post_params = {
        'chip_cfg': chip.schema.cfg,
        'params': __build_post_params(chip,
                                      job_hash=chip.status['jobhash'])
    }

    def post_action(url):
        upload_file.seek(0)
        return requests.post(url,
                             files={'import': upload_file,
                                    'params': json.dumps(post_params)},
                             timeout=__timeout)

    def success_action(resp):
        chip.logger.info(resp.text)

    __post(chip, '/remote_run/', post_action, success_action)
    upload_file.close()


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
                                     job_hash=chip.status['jobhash'],
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
        info = {
            'busy': ("Job has no running steps." not in resp.text),
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
def delete_job(chip):
    '''
    Helper method to delete a job from shared remote storage.
    '''

    def post_action(url):
        return requests.post(url,
                             data=json.dumps(__build_post_params(chip,
                                                                 job_hash=chip.status['jobhash'])),
                             timeout=__timeout)

    def success_action(resp):
        return resp.text

    return __post(chip, '/delete_job/', post_action, success_action)


###################################
def fetch_results_request(chip, node='', results_path):
    '''
    Helper method to fetch job results from a remote compute cluster.
    Optional 'node' argument fetches results for only the specified
    flowgraph node (e.g. "floorplan0")

       Returns:
       * 0 if no error was encountered.
       * [response code] if the results could not be retrieved.
    '''

    # Set the request URL.
    job_hash = chip.status['jobhash']

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

        return __post(chip,
                      f'/get_results/{job_hash}.tar.gz',
                      post_action,
                      success_action)


###################################
def fetch_results(chip, node='', results_path=None):
    '''
    Helper method to fetch and open job results from a remote compute cluster.
    Optional 'node' argument fetches results for only the specified
    flowgraph node (e.g. "floorplan0")
    '''

    # Set default results archive path if necessary, and fetch it.
    if not results_path:
        results_path=f'{job_hash}{node}.tar.gz'
    results_code = fetch_results_request(chip, node, results_path)

    # Note: the server should eventually delete the results as they age out (~8h), but this will
    # give us a brief period to look at failed results.
    if results_code:
        chip.error("Sorry, something went wrong and your job results could not be retrieved. "
                   f"(Response code: {results_code})", fatal=True)

    # Call 'delete_job' to remove the run from the server.
    if not node:
        delete_job(chip)

    # Unzip the results.
    top_design = chip.get('design')
    job_hash = chip.status['jobhash']
    local_dir = chip.get('option', 'builddir')

    # Unauthenticated jobs get a gzip archive, authenticated jobs get nested archives.
    # So we need to extract and delete those.
    # Archive contents: server-side build directory. Format:
    # [job_hash]/[design]/[job_name]/[step]/[index]/...
    with tarfile.open(results_path, 'r:gz') as tar:
        tar.extractall(path=(node if node else ''))
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
    Helper method to call check_user on server
    '''

    # Make the request and print its response.
    def post_action(url):
        return requests.post(url,
                             data=json.dumps(__build_post_params(chip)),
                             timeout=__timeout)

    def success_action(resp):
        return resp.json()

    user_info = __post(chip, '/check_user/', post_action, success_action)
    if not user_info:
        raise ValueError('Server response is not valid.')

    if ('compute_time' not in user_info) or \
       ('bandwidth_kb' not in user_info):
        print('Error fetching user information from the remote server.')
        raise ValueError(f'Server response is not valied or missing fields: {user_info}')

    if 'remote_cfg' in chip.status:
        remote_cfg = chip.status['remote_cfg']
        # Print the user's account info, and return.
        print(f'User {remote_cfg["username"]}:')
    print(f'  Remaining compute time: {(user_info["compute_time"]/60.0):.2f} minutes')
    print(f'  Remaining results bandwidth: {user_info["bandwidth_kb"]} KiB')
