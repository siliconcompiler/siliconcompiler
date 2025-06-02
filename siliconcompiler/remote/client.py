# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import json
import os
import requests
import shutil
import time
import urllib.parse
import tarfile
import tempfile
import multiprocessing

import os.path

from siliconcompiler import utils, SiliconCompilerError
from siliconcompiler import NodeStatus as SCNodeStatus
from siliconcompiler._metadata import default_server
from siliconcompiler.remote import JobStatus, NodeStatus
from siliconcompiler.report.dashboard import DashboardType
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.schema import JournalingSchema

# Step name to use while logging
remote_step_name = 'remote'


class Client():
    # Step name to use while logging
    STEP_NAME = "remote"

    def __init__(self, chip, default_server=default_server):
        self.__chip = chip
        self.__logger = self.__chip.logger.getChild('remote-client')

        self.__default_server = default_server

        # Used when reporting node information during run
        self.__maxlinelength = 70

        self.__init_config()
        self.__init_baseurl()

        # Client / server timeout
        self.__timeout = 10
        self.__max_timeouts = 10
        self.__tos_str = '''Please review the SiliconCompiler cloud's terms of service:

https://www.siliconcompiler.com/terms

In particular, please ensure that you have the right to distribute any IP
which is contained in designs that you upload to the service. This public
service, provided by SiliconCompiler, is not intended to process proprietary IP.
'''
        # Runtime
        self.__download_pool = None
        self.__check_interval = None
        self.__node_information = None

    def __get_remote_config_file(self, fail=True):
        if self.__chip.get('option', 'credentials'):
            # Use the provided remote credentials file.
            cfg_file = os.path.abspath(self.__chip.get('option', 'credentials'))

            if fail and not os.path.isfile(cfg_file) and \
               getattr(self, '_error_on_missing_file', True):
                # Check if it's a file since its been requested by the user
                raise SiliconCompilerError(
                    f'Unable to find the credentials file: {cfg_file}',
                    chip=self.__chip)
        else:
            # Use the default config file path.
            cfg_file = utils.default_credentials_file()

        return cfg_file

    def __init_config(self):
        cfg_file = self.__get_remote_config_file()

        remote_cfg = {}
        cfg_dir = os.path.dirname(cfg_file)
        if os.path.isdir(cfg_dir) and os.path.isfile(cfg_file):
            self.__logger.info(f'Using credentials: {cfg_file}')
            with open(cfg_file, 'r') as cfgf:
                remote_cfg = json.loads(cfgf.read())
        else:
            if getattr(self, '_print_server_warning', True):
                self.__logger.warning('Could not find remote server configuration: '
                                      f'defaulting to {self.__default_server}')
            remote_cfg = {
                "address": self.__default_server,
                "directory_whitelist": []
            }
        if 'address' not in remote_cfg:
            raise SiliconCompilerError(
                'Improperly formatted remote server configuration - '
                'please run "sc-remote -configure" and enter your server address and '
                'credentials.', chip=self.__chip)

        self.__config = remote_cfg

    def __init_baseurl(self):
        remote_host = self.__config['address']
        if 'port' in self.__config:
            remote_port = self.__config['port']
        else:
            remote_port = 443
        remote_host += f':{remote_port}'
        if remote_host.startswith('http'):
            remote_protocol = ''
        else:
            remote_protocol = 'https://' if remote_port == 443 else 'http://'
        self.__url = remote_protocol + remote_host

    def __get_url(self, action):
        return urllib.parse.urljoin(self.__url, action)

    def remote_manifest(self):
        return f'{self.__chip.getworkdir()}/sc_remote.pkg.json'

    def print_configuration(self):
        self.__logger.info(f'Server: {self.__url}')
        if 'username' in self.__config:
            self.__logger.info(f'Username: {self.__config["username"]}')
        if 'directory_whitelist' in self.__config and self.__config['directory_whitelist']:
            self.__logger.info('Directory whitelist:')
            for path in sorted(self.__config['directory_whitelist']):
                self.__logger.info(f'  {path}')

    def __get_post_params(self, include_job_name=False, include_job_id=False):
        '''
        Helper function to build the params for the post request
        '''
        # Use authentication if necessary.
        post_params = {}

        if include_job_id and self.__chip.get('record', 'remoteid'):
            post_params['job_hash'] = self.__chip.get('record', 'remoteid')

        if include_job_name and self.__chip.get('option', 'jobname'):
            post_params['job_id'] = self.__chip.get('option', 'jobname')

        # Forward authentication information
        if ('username' in self.__config) and ('password' in self.__config) and \
           (self.__config['username']) and (self.__config['password']):
            post_params['username'] = self.__config['username']
            post_params['key'] = self.__config['password']

        return post_params

    ###################################
    def __post(self, action, post_action, success_action, error_action=None):
        '''
        Helper function to handle the post request
        '''
        redirect_url = self.__get_url(action)

        timeouts = 0
        while redirect_url:
            try:
                resp = post_action(redirect_url)
            except requests.Timeout:
                timeouts += 1
                if timeouts > self.__max_timeouts:
                    raise SiliconCompilerError('Server communications timed out', chip=self.__chip)
                time.sleep(self.__timeout)
                continue
            except Exception as e:
                raise SiliconCompilerError(f'Server communications error: {e}', chip=self.__chip)

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
                raise SiliconCompilerError(f'Server responded with {code}: {msg}', chip=self.__chip)

    def cancel_job(self):
        '''
        Helper method to request that the server cancel an ongoing job.
        '''

        def post_action(url):
            return requests.post(
                url,
                data=json.dumps(self.__get_post_params(
                    include_job_id=True
                )),
                timeout=self.__timeout)

        def success_action(resp):
            return json.loads(resp.text)

        return self.__post('/cancel_job/', post_action, success_action)

    ###################################
    def delete_job(self):
        '''
        Helper method to delete a job from shared remote storage.
        '''

        def post_action(url):
            return requests.post(
                url,
                data=json.dumps(self.__get_post_params(
                    include_job_id=True
                )),
                timeout=self.__timeout)

        def success_action(resp):
            return resp.text

        return self.__post('/delete_job/', post_action, success_action)

    def check_job_status(self):
        # Make the request and print its response.
        def post_action(url):
            return requests.post(
                url,
                data=json.dumps(self.__get_post_params(include_job_id=True, include_job_name=True)),
                timeout=self.__timeout)

        def error_action(code, msg):
            return {
                'busy': True,
                'message': ''
            }

        def success_action(resp):
            json_response = json.loads(resp.text)

            if json_response['status'] != JobStatus.RUNNING:
                if json_response['status'] == JobStatus.REJECTED:
                    self.__logger.error(f'Job was rejected: {json_response["message"]}')
                elif json_response['status'] != JobStatus.UNKNOWN:
                    self.__logger.info(f'Job status: {json_response["status"]}')
            info = {
                'busy': json_response['status'] == JobStatus.RUNNING,
                'message': None
            }

            if isinstance(json_response['message'], str):
                info['message'] = json_response['message']
            else:
                info['message'] = json.dumps(json_response['message'])
            return info

        info = self.__post(
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

    def __log_node_status(self, status, nodes):
        '''
        Helper method to log truncated information about flowgraph nodes
        with a given status, on a single line.
        Used to print info about all statuses besides NodeStatus.RUNNING.
        '''

        num_nodes = len(nodes)
        if num_nodes > 0:
            line_len = 0
            nodes_log = f'  {status.title()} ({num_nodes}): '
            log_nodes = []
            for node, _ in nodes:
                node_len = len(node)

                if node_len + line_len + 2 < self.__maxlinelength:
                    log_nodes.append(node)
                    line_len += node_len + 2
                else:
                    if len(log_nodes) == num_nodes - 1:
                        log_nodes.append(node)
                    else:
                        log_nodes.append('...')
                    break

            nodes_log += ', '.join(log_nodes)
            self.__logger.info(nodes_log)

    def _report_job_status(self, info):
        completed = []
        starttimes = {}

        if not info['busy']:
            # Job is not running
            return completed, starttimes, False

        try:
            # Decode response JSON, if possible.
            job_info = json.loads(info['message'])
            if "null" in job_info:
                job_info[None] = job_info["null"]
                del job_info["null"]
        except json.JSONDecodeError:
            self.__logger.warning(f"Job is still running: {info['message']}")
            return completed, starttimes, True

        nodes_to_log = {}
        for node, node_info in job_info.items():
            status = node_info['status']

            if status == NodeStatus.UPLOADED:
                status = SCNodeStatus.PENDING

            if SCNodeStatus.is_done(status):
                # collect completed
                completed.append(node)

            if not node:
                continue

            nodes_to_log.setdefault(status, []).append((node, node_info))

            if self.__node_information and node in self.__node_information:
                self.__chip.set('record', 'status', status,
                                step=self.__node_information[node]["step"],
                                index=self.__node_information[node]["index"])

        nodes_to_log = {key: nodes_to_log[key] for key in sorted(nodes_to_log.keys())}

        # Log information about the job's progress.
        self.__logger.info("Job is still running. Status:")

        for stat, nodes in nodes_to_log.items():
            if SCNodeStatus.is_done(stat):
                self.__log_node_status(stat, nodes)

        # Running / in-progress flowgraph nodes should all be printed:
        base_time = time.time()
        for stat, nodes in nodes_to_log.items():
            for node, node_info in nodes:
                if 'elapsed_time' in node_info:
                    runtime = 0
                    for part in node_info['elapsed_time'].split(":"):
                        runtime = 60 * runtime + float(part)
                    starttimes[(self.__node_information[node]["step"],
                                self.__node_information[node]["index"])] = base_time - runtime

            if SCNodeStatus.is_running(stat):
                self.__logger.info(f'  {stat.title()} ({len(nodes)}):')
                for node, node_info in nodes:
                    running_log = f"    {node}"
                    if 'elapsed_time' in node_info:
                        running_log += f" ({node_info['elapsed_time']})"
                    self.__logger.info(running_log)

        # Queued and pending flowgraph nodes:
        for stat, nodes in nodes_to_log.items():
            if SCNodeStatus.is_waiting(stat):
                self.__log_node_status(stat, nodes)

        return completed, starttimes, True

    def __check(self):
        def post_action(url):
            return requests.post(
                url,
                data=json.dumps(self.__get_post_params()),
                timeout=self.__timeout)

        def success_action(resp):
            return resp.json()

        response_info = self.__post('/check_server/', post_action, success_action)
        if not response_info:
            raise ValueError('Server response is not valid.')

        return response_info

    def check(self):
        '''
        Helper method to call check_server on server
        '''

        # Make the request and print its response.
        response_info = self.__check()

        # Print status value.
        server_status = response_info['status']
        self.__logger.info(f'Server status: {server_status}')
        if server_status != 'ready':
            self.__logger.warning('  Status is not "ready", server cannot accept new jobs.')

        # Print server-side version info.
        version_info = response_info['versions']
        version_suffix = ' version'
        max_name_string_len = max([len(s) for s in version_info.keys()]) + len(version_suffix)
        self.__logger.info('Server software versions:')
        for name, version in version_info.items():
            print_name = f'{name}{version_suffix}'
            self.__logger.info(f'  {print_name: <{max_name_string_len}}: {version}')

        # Print user info if applicable.
        if 'user_info' in response_info:
            user_info = response_info['user_info']
            if ('compute_time' not in user_info) or \
               ('bandwidth_kb' not in user_info):
                self.__logger.info('Error fetching user information from the remote server.')
                raise ValueError(f'Server response is not valid or missing fields: {user_info}')

            if 'username' in self.__config:
                # Print the user's account info, and return.
                self.__logger.info(f'User {self.__config["username"]}:')

            time_remaining = user_info["compute_time"] / 60.0
            bandwidth_remaining = user_info["bandwidth_kb"]
            self.__logger.info(f'  Remaining compute time: {(time_remaining):.2f} minutes')
            self.__logger.info(f'  Remaining results bandwidth: {bandwidth_remaining} KiB')

        self.__print_tos(response_info)

        # Return the response info in case the caller wants to inspect it.
        return response_info

    def __print_tos(self, response_info):
        # Print terms-of-service message, if the server provides one.
        if 'terms' in response_info and response_info['terms']:
            self.__logger.info('Terms of Service info for this server:')
            for line in response_info['terms'].splitlines():
                if line:
                    self.__logger.info(line)

    def run(self):
        '''
        Dispatch the Chip to a remote server for processing.
        '''
        should_resume = not self.__chip.get('option', 'clean')
        remote_resume = should_resume and self.__chip.get('record', 'remoteid')

        # Pre-process: Run an starting nodes locally, and upload the
        # in-progress build directory to the remote server.
        # Data is encrypted if user / key were specified.
        # run remote process
        if self.__chip.get('arg', 'step'):
            raise SiliconCompilerError('Cannot pass [arg,step] parameter into remote flow.',
                                       chip=self.__chip)
        if self.__chip.get('arg', 'index'):
            raise SiliconCompilerError('Cannot pass [arg,index] parameter into remote flow.',
                                       chip=self.__chip)

        if not self.__chip._dash:
            self.__chip.dashboard(type=DashboardType.CLI)

        # Only run the pre-process step if the job doesn't already have a remote ID.
        if not remote_resume:
            self.__run_preprocess()

        # Run the job on the remote server, and wait for it to finish.
        # Set logger to indicate remote run
        self.__chip._init_logger(step=self.STEP_NAME, index=None, in_run=True)

        # Ask the remote server to start processing the requested step.
        self.__request_run()

        # Run the main 'check_progress' loop to monitor job status until it finishes.
        try:
            self._run_loop()
        finally:
            # Restore logger
            self.__chip._dash.end_of_run()
            self.__chip._init_logger(in_run=True)

    def __request_run(self):
        '''
        Helper method to make a web request to start a job stage.
        '''

        remote_status = self.__check()

        if remote_status['status'] != 'ready':
            raise SiliconCompilerError('Remote server is not available.', chip=self.__chip)

        self.__print_tos(remote_status)

        remote_resume = not self.__chip.get('option', 'clean') and \
            self.__chip.get('record', 'remoteid')
        # Only package and upload the entry steps if starting a new job.
        if not remote_resume:
            upload_file = tempfile.TemporaryFile(prefix='sc', suffix='remote.tar.gz')
            with tarfile.open(fileobj=upload_file, mode='w:gz') as tar:
                tar.add(self.__chip.getworkdir(), arcname='')
            # Flush file to ensure everything is written
            upload_file.flush()

            # We no longer need the collected files
            shutil.rmtree(self.__chip._getcollectdir(jobname=self.__chip.get('option', 'jobname')))

        if 'pre_upload' in remote_status:
            self.__logger.info(remote_status['pre_upload']['message'])
            time.sleep(remote_status['pre_upload']['delay'])

        # Make the actual request, streaming the bulk data as a multipart file.
        # Redirected POST requests are translated to GETs. This is actually
        # part of the HTTP spec, so we need to manually follow the trail.
        post_params = {
            'chip_cfg': self.__chip.schema.getdict(),
            'params': self.__get_post_params(include_job_id=True)
        }

        post_files = {'params': json.dumps(post_params)}
        if not remote_resume:
            post_files['import'] = upload_file
            upload_file.seek(0)

        def post_action(url):
            return requests.post(
                url,
                files=post_files,
                timeout=self.__timeout)

        def success_action(resp):
            return resp.json()

        resp = self.__post('/remote_run/', post_action, success_action)
        if not remote_resume:
            upload_file.close()

        if 'message' in resp and resp['message']:
            self.__logger.info(resp['message'])
        self.__chip.set('record', 'remoteid', resp['job_hash'])

        self.__chip.write_manifest(self.remote_manifest())

        self.__logger.info(f"Your job's reference ID is: {resp['job_hash']}")

        self.__check_interval = remote_status['progress_interval']

    def __run_preprocess(self):
        '''
        Helper method to run a local import stage for remote jobs.
        '''

        # Ensure packages with python sources are copied
        for key in self.__chip.allkeys():
            key_type = self.__chip.get(*key, field='type')

            if 'dir' in key_type or 'file' in key_type:
                for _, step, index in self.__chip.schema.get(*key, field=None).getvalues(
                        return_defvalue=False):
                    packages = self.__chip.get(*key, field='package', step=step, index=index)
                    if not isinstance(packages, list):
                        packages = [packages]
                    force_copy = False
                    for package in packages:
                        if not package:
                            continue
                        if package.startswith('python://'):
                            force_copy = True
                    if force_copy:
                        self.__chip.set(*key, True, field='copy', step=step, index=index)

        # Collect inputs into a collection directory only for remote runs, since
        # we need to send inputs up to the server.
        self.__chip.collect(whitelist=self.__config.setdefault('directory_whitelist', []))

    def _run_loop(self):
        # Wrapper to allow for capturing of Ctrl+C
        try:
            self.__run_loop()
            self._finalize_loop()
        except KeyboardInterrupt:
            manifest_path = self.remote_manifest()
            reconnect_cmd = f'sc-remote -cfg {manifest_path} -reconnect'
            cancel_cmd = f'sc-remote -cfg {manifest_path} -cancel'
            self.__logger.info('Disconnecting from remote job')
            self.__logger.info(f'To reconnect to this job use: {reconnect_cmd}')
            self.__logger.info(f'To cancel this job use: {cancel_cmd}')
            raise SiliconCompilerError('Job canceled by user keyboard interrupt')

    def __import_run_manifests(self, starttimes):
        if not self.__setup_information_loaded:
            if self.__setup_information_fetched:
                manifest = os.path.join(self.__chip.getworkdir(), f'{self.__chip.design}.pkg.json')
                if os.path.exists(manifest):
                    try:
                        JournalingSchema(self.__chip.schema).read_journal(manifest)
                        self.__setup_information_loaded = True
                        changed = True
                    except:  # noqa E722
                        # Import may fail if file is still getting written
                        pass

        if not self.__setup_information_loaded:
            # Dont do anything until this has been loaded
            return

        changed = False
        for _, node_info in self.__node_information.items():
            if node_info["imported"]:
                continue

            manifest = os.path.join(
                self.__chip.getworkdir(step=node_info["step"], index=node_info["index"]),
                'outputs',
                f'{self.__chip.design}.pkg.json')
            if os.path.exists(manifest):
                try:
                    JournalingSchema(self.__chip.schema).read_journal(manifest)
                    node_info["imported"] = True
                    changed = True
                except:  # noqa E722
                    # Import may fail if file is still getting written
                    pass
            elif self.__chip.get('record', 'status',
                                 step=node_info["step"], index=node_info["index"]) \
                    == SCNodeStatus.SKIPPED:
                node_info["imported"] = True
                changed = True

        if changed and self.__chip._dash:
            # Update dashboard if active
            self.__chip._dash.update_manifest({"starttimes": starttimes})

        return changed

    def __ensure_run_loop_information(self):
        self.__chip._init_logger(step=self.STEP_NAME, index='0', in_run=True)
        if not self.__download_pool:
            self.__download_pool = multiprocessing.Pool()

        if self.__check_interval is None:
            check_info = self.__check()
            self.__check_interval = check_info['progress_interval']

        self.__setup_information_fetched = False
        self.__setup_information_loaded = False

        self.__node_information = {}
        runtime = RuntimeFlowgraph(
            self.__chip.schema.get("flowgraph", self.__chip.get('option', 'flow'), field='schema'),
            from_steps=self.__chip.get('option', 'from'),
            to_steps=self.__chip.get('option', 'to'),
            prune_nodes=self.__chip.get('option', 'prune'))

        for step, index in runtime.get_nodes():
            done = SCNodeStatus.is_done(self.__chip.get('record', 'status', step=step, index=index))
            node_info = {
                "step": step,
                "index": index,
                "imported": done,
                "fetched": done
            }
            self.__node_information[f'{step}{index}'] = node_info

    def __run_loop(self):
        self.__ensure_run_loop_information()

        # Check the job's progress periodically until it finishes.
        running = True

        starttimes = {}

        while running:
            sleepremaining = self.__check_interval
            while any([nodeinfo["fetched"] and not nodeinfo["imported"]
                       for nodeinfo in self.__node_information.values()]):
                self.__import_run_manifests(starttimes)
                sleepremaining -= 1
                if sleepremaining <= 0:
                    break
                time.sleep(1)
            if sleepremaining > 0:
                time.sleep(sleepremaining)

            # Check progress
            job_info = self.check_job_status()
            completed, new_starttimes, running = self._report_job_status(job_info)

            # preserve old starttimes
            starttimes = {**starttimes, **new_starttimes}

            if self.__chip._dash:
                # Update dashboard if active
                self.__chip._dash.update_manifest({"starttimes": starttimes})

            if None in completed:
                completed.remove(None)
                if not self.__setup_information_fetched:
                    self.__schedule_fetch_result(None)

            nodes_to_fetch = []
            for node in completed:
                if not self.__node_information[node]["fetched"]:
                    nodes_to_fetch.append(node)

            if nodes_to_fetch:
                self.__logger.info('  Fetching completed results:')
                for node in nodes_to_fetch:
                    self.__schedule_fetch_result(node)

        # Done: try to fetch any node results which still haven't been retrieved.
        self.__logger.info('Remote job completed! Retrieving final results...')
        for node, node_info in self.__node_information.items():
            if not node_info["fetched"]:
                self.__schedule_fetch_result(node)

        self._finalize_loop()

        # Un-set the 'remote' option to avoid from/to-based summary/show errors
        self.__chip.unset('option', 'remote')

        if self.__chip._dash:
            self.__chip._dash.update_manifest()

    def _finalize_loop(self):
        if self.__download_pool:
            self.__download_pool.close()
            self.__download_pool.join()
            self.__download_pool = None

        self.__import_run_manifests({})

    def __schedule_fetch_result(self, node):
        if node:
            self.__node_information[node]["fetched"] = True
            self.__logger.info(f'    {node}')
        else:
            self.__setup_information_fetched = True
        self.__download_pool.apply_async(Client._fetch_result, (self, node))

    def _fetch_result(self, node):
        '''
        Helper method to fetch and open job results from a remote compute cluster.
        Optional 'node' argument fetches results for only the specified
        flowgraph node (e.g. "floorplan0")
        '''

        # Collect local values.
        job_hash = self.__chip.get('record', 'remoteid')
        local_dir = self.__chip.get('option', 'builddir')

        # Set default results archive path if necessary, and fetch it.
        with tempfile.TemporaryDirectory(prefix=f'sc_{job_hash}_', suffix=f'_{node}') as tmpdir:
            results_path = os.path.join(tmpdir, 'result.tar.gz')

            with open(results_path, 'wb') as rd:
                # Fetch results archive.
                def post_action(url):
                    post_params = self.__get_post_params()
                    if node:
                        post_params['node'] = node
                    return requests.post(
                        url,
                        data=json.dumps(post_params),
                        stream=True,
                        timeout=self.__timeout)

                def success_action(resp):
                    shutil.copyfileobj(resp.raw, rd)
                    return 0

                def error_action(code, msg):
                    # Results are fetched in parallel, and a failure in one node
                    # does not necessarily mean that the whole job failed.
                    if node:
                        self.__logger.warning(f'Could not fetch results for node: {node}')
                    else:
                        self.__logger.warning('Could not fetch results for final results.')
                    return 404

                results_code = self.__post(
                    f'/get_results/{job_hash}.tar.gz',
                    post_action,
                    success_action,
                    error_action=error_action
                )

            # Note: the server should eventually delete the results as they age out (~8h),
            # but this will give us a brief period to look at failed results.
            if results_code:
                return

            # Unzip the results.
            # Unauthenticated jobs get a gzip archive, authenticated jobs get nested archives.
            # So we need to extract and delete those.
            # Archive contents: server-side build directory. Format:
            # [job_hash]/[design]/[job_name]/[step]/[index]/...
            try:
                with tarfile.open(results_path, 'r:gz') as tar:
                    tar.extractall(path=tmpdir)
            except tarfile.TarError as e:
                self.__logger.error(f'Failed to extract data from {results_path}: {e}')
                return

            work_dir = os.path.join(tmpdir, job_hash)
            if os.path.exists(work_dir):
                shutil.copytree(work_dir, local_dir, dirs_exist_ok=True)
            else:
                self.__logger.error(f'Empty file returned from remote for: {node}')
                return

    def configure_server(self, server=None, username=None, password=None):

        def confirm_dialog(message):
            confirmed = False
            while not confirmed:
                oin = input(f'{message} y/N: ')
                if (not oin) or (oin == 'n') or (oin == 'N'):
                    return False
                elif (oin == 'y') or (oin == 'Y'):
                    return True
            return False

        default_server_name = urllib.parse.urlparse(self.__default_server).hostname

        # Find the config file/directory path.
        cfg_file = self.__get_remote_config_file()
        cfg_dir = os.path.dirname(cfg_file)

        # Create directory if it doesn't exist.
        if cfg_dir and not os.path.isdir(cfg_dir):
            os.makedirs(cfg_dir, exist_ok=True)

        # If an existing config file exists, prompt the user to overwrite it.
        if os.path.isfile(cfg_file):
            if not confirm_dialog('Overwrite existing remote configuration?'):
                return

        self.__config = {}

        # If a command-line argument is passed in, use that as a public server address.
        if server:
            srv_addr = server
            self.__logger.info(f'Creating remote configuration file for server: {srv_addr}')
        else:
            # If no arguments were passed in, interactively request credentials from the user.
            srv_addr = input('Remote server address (leave blank to use default server):\n')
            srv_addr = srv_addr.replace(" ", "")

        if not srv_addr:
            srv_addr = self.__default_server
            self.__logger.info(f'Using {srv_addr} as server')

        server = urllib.parse.urlparse(srv_addr)
        has_scheme = True
        if not server.hostname:
            # fake add a scheme to the url
            has_scheme = False
            server = urllib.parse.urlparse('https://' + srv_addr)
        if not server.hostname:
            raise ValueError(f'Invalid address provided: {srv_addr}')

        if has_scheme:
            self.__config['address'] = f'{server.scheme}://{server.hostname}'
        else:
            self.__config['address'] = server.hostname

        public_server = default_server_name in srv_addr
        if public_server and not confirm_dialog(self.__tos_str):
            return

        if server.port is not None:
            self.__config['port'] = server.port

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
                self.__config['username'] = username
            if password:
                self.__config['password'] = password

        self.__config['directory_whitelist'] = []

        # Save the values to the target config file in JSON format.
        with open(cfg_file, 'w') as f:
            f.write(json.dumps(self.__config, indent=4))

        # Let the user know that we finished successfully.
        self.__logger.info(f'Remote configuration saved to: {cfg_file}')

    def configure_whitelist(self, add=None, remove=None):
        cfg_file = self.__get_remote_config_file()

        self.__logger.info(f'Updating credentials: {cfg_file}')

        if 'directory_whitelist' not in self.__config:
            self.__config['directory_whitelist'] = []

        if add:
            for path in add:
                path = os.path.abspath(path)
                self.__logger.info(f'Adding {path}')
                self.__config['directory_whitelist'].append(path)

        if remove:
            for path in remove:
                path = os.path.abspath(path)
                if path in self.__config['directory_whitelist']:
                    self.__logger.info(f'Removing {path}')
                    self.__config['directory_whitelist'].remove(path)

        # Cleanup
        self.__config['directory_whitelist'] = list(set(self.__config['directory_whitelist']))

        # Save the values to the target config file in JSON format.
        with open(cfg_file, 'w') as f:
            f.write(json.dumps(self.__config, indent=4))

    #######################################
    def __getstate__(self):
        # Called when generating a serial stream of the object
        attributes = self.__dict__.copy()

        attributes['_Client__download_pool'] = None

        return attributes


class ConfigureClient(Client):
    def __init__(self, chip):
        self._print_server_warning = False
        self._error_on_missing_file = False

        super().__init__(chip)
