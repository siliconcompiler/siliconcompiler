import json
import os
import pytest
import requests
import time

import os.path

from siliconcompiler import NodeStatus
from siliconcompiler.remote import Client
from siliconcompiler.remote import NodeStatus as RemoteNodeStatus
from siliconcompiler.remote.server import Server


def _client(project, nodes=('stepone0', 'steptwo0')):
    '''A client with the node table __run_loop() would have built for it.'''
    client = Client(project)
    client._Client__node_information = {
        node: {
            "step": node[:-1],
            "index": node[-1],
            "imported": False,
            "fetched": False,
            "print": f"{node[:-1]}/{node[-1]}"
        } for node in nodes
    }
    return client


def _status(busy, message):
    return {'busy': busy, 'message': message}


###########################
# _report_job_status
###########################

def test_report_job_status_finished(gcd_nop_project):
    '''A job that is not running ends the wait loop'''
    client = _client(gcd_nop_project)

    completed, starttimes, running = client._report_job_status(
        _status(False, 'Job has no running steps.'))

    assert running is False
    assert completed == []
    assert starttimes == {}


def test_report_job_status_unparsable_message(gcd_nop_project, caplog):
    '''A message that is not the node payload is reported, not crashed on'''
    client = _client(gcd_nop_project)

    completed, starttimes, running = client._report_job_status(
        _status(True, 'Job is being scheduled'))

    assert running is True
    assert completed == []
    assert 'Job is still running: Job is being scheduled' in caplog.text


def test_report_job_status_running_nodes(gcd_nop_project):
    '''Node statuses are recorded and elapsed times become start times'''
    client = _client(gcd_nop_project)

    payload = {
        'null': {'status': NodeStatus.SUCCESS},
        'stepone0': {'status': NodeStatus.SUCCESS, 'elapsed_time': '0:00:30'},
        'steptwo0': {'status': NodeStatus.RUNNING, 'elapsed_time': '0:01:05'}
    }

    before = time.time()
    completed, starttimes, running = client._report_job_status(
        _status(True, json.dumps(payload)))

    assert running is True
    # The 'null' key is the setup manifest, which the loop fetches as None.
    assert sorted(completed, key=str) == [None, 'stepone0']

    # 65s of elapsed time means the node started 65s ago, and 30s means 30.
    assert before - 66 <= starttimes[('steptwo', '0')] <= before - 64
    assert before - 31 <= starttimes[('stepone', '0')] <= before - 29

    assert gcd_nop_project.get('record', 'status', step='stepone', index='0') == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.get('record', 'status', step='steptwo', index='0') == \
        NodeStatus.RUNNING


def test_report_job_status_uploaded_is_pending(gcd_nop_project):
    '''A node the client ran itself is reported back as uploaded, and is
       pending as far as this run is concerned'''
    client = _client(gcd_nop_project)

    payload = {'stepone0': {'status': RemoteNodeStatus.UPLOADED}}

    completed, _, running = client._report_job_status(
        _status(True, json.dumps(payload)))

    assert running is True
    assert completed == []
    assert gcd_nop_project.get('record', 'status', step='stepone', index='0') == \
        NodeStatus.PENDING


def test_report_job_status_without_elapsed_time(gcd_nop_project):
    '''A server that reports no timing still drives the loop'''
    client = _client(gcd_nop_project)

    payload = {
        'stepone0': {'status': NodeStatus.RUNNING},
        'steptwo0': {'status': NodeStatus.PENDING}
    }

    completed, starttimes, running = client._report_job_status(
        _status(True, json.dumps(payload)))

    assert running is True
    assert completed == []
    assert starttimes == {}


def test_report_job_status_truncates_long_lists(gcd_nop_project, caplog):
    '''A status shared by more nodes than fit on a line is truncated'''
    nodes = [f'node{num}0' for num in range(12)]
    client = _client(gcd_nop_project, nodes=nodes)

    payload = {node: {'status': NodeStatus.SUCCESS} for node in nodes}

    client._report_job_status(_status(True, json.dumps(payload)))

    logged = [line for line in caplog.text.splitlines() if 'Success (12)' in line]
    assert len(logged) == 1
    assert logged[0].endswith('...')


def test_report_job_status_reads_server_payload(gcd_nop_project):
    '''The client parses what the server actually sends.

    Both halves of 'check_progress' are exercised here rather than a
    hand-written payload, so a change to one that the other cannot read fails.
    '''
    server = Server()
    server.set('option', 'nfsmount', os.path.abspath('mount'))

    job_hash = 'a' * 32
    now = time.time()
    server.sc_jobs[job_hash] = {
        None: {'status': NodeStatus.SUCCESS},
        'stepone0': {'status': NodeStatus.SUCCESS, 'step': 'stepone', 'index': '0',
                     'starttime': now - 90, 'endtime': now - 30},
        'steptwo0': {'status': NodeStatus.RUNNING, 'step': 'steptwo', 'index': '0',
                     'starttime': now - 12}
    }
    message = server._Server__progress_message(job_hash)

    client = _client(gcd_nop_project)
    completed, starttimes, running = client._report_job_status(
        _status(True, json.dumps(message)))

    assert running is True
    assert sorted(completed, key=str) == [None, 'stepone0']
    # 0:01:00 of recorded runtime for the finished node, 0:00:12 for the running one.
    assert now - 61 <= starttimes[('stepone', '0')] <= now - 59
    assert now - 13 <= starttimes[('steptwo', '0')] <= now - 11


###########################
# Fetching results
###########################

@pytest.mark.timeout(60)
def test_fetch_results_inline(gcd_remote_test, inline_download_pool):
    '''Results are downloaded, unpacked and merged into the local build.

    Runs the download in this process rather than in a pool worker, so the
    fetch is actually exercised here instead of in a subprocess nothing can
    see.
    '''
    project = gcd_remote_test()

    assert project.run()

    assert inline_download_pool, 'the client never built a download pool'
    fetched = [args[1] for pool in inline_download_pool for args in pool.calls]
    assert None in fetched, 'the setup manifest was never fetched'
    assert 'stepone0' in fetched

    assert os.path.isfile('build/gcd/job0/stepone/0/outputs/gcd.pkg.json')
    assert os.path.isfile('build/gcd/job0/steptwo/0/outputs/gcd.pkg.json')


@pytest.mark.timeout(60)
def test_fetch_results_missing_node(gcd_remote_test, inline_download_pool, caplog):
    '''A node with nothing to fetch is reported, and the run is not derailed'''
    project = gcd_remote_test()
    project.set('record', 'remoteid', 'b' * 32)

    client = Client(project)
    client._fetch_result('nosuchnode0')

    assert 'Could not fetch results for node: nosuchnode0' in caplog.text


###########################
# Server communication
###########################

def _response(code, text='', headers=None):
    resp = requests.Response()
    resp.status_code = code
    resp.encoding = 'ascii'
    resp._content = bytes(text, encoding='ascii')
    if headers:
        resp.headers.update(headers)
    return resp


def test_post_retries_timeouts(gcd_nop_project, monkeypatch):
    '''A timeout is retried rather than failing the job'''
    monkeypatch.setattr('siliconcompiler.remote.client.time.sleep', lambda _: None)

    attempts = []

    def flaky_post(url, **kwargs):
        attempts.append(url)
        if len(attempts) < 3:
            raise requests.Timeout()
        return _response(200, 'Job deleted.')

    monkeypatch.setattr(requests, 'post', flaky_post)

    assert Client(gcd_nop_project).delete_job() == 'Job deleted.'
    assert len(attempts) == 3


def test_post_gives_up_on_repeated_timeouts(gcd_nop_project, monkeypatch):
    '''Timeouts that never clear end the attempt'''
    monkeypatch.setattr('siliconcompiler.remote.client.time.sleep', lambda _: None)

    def always_timeout(url, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, 'post', always_timeout)

    with pytest.raises(TimeoutError, match='Server communications timed out'):
        Client(gcd_nop_project).delete_job()


def test_post_follows_redirect(gcd_nop_project, monkeypatch):
    '''A redirected POST is followed, since the spec turns it into a GET'''
    urls = []

    def redirecting_post(url, **kwargs):
        urls.append(url)
        if len(urls) == 1:
            return _response(302, headers={'Location': 'http://elsewhere/delete_job/'})
        return _response(200, 'Job deleted.')

    monkeypatch.setattr(requests, 'post', redirecting_post)

    assert Client(gcd_nop_project).delete_job() == 'Job deleted.'
    assert urls[1] == 'http://elsewhere/delete_job/'


def test_post_raises_on_error_without_handler(gcd_nop_project, monkeypatch):
    '''An error with no handler for it is surfaced'''
    monkeypatch.setattr(requests, 'post',
                        lambda url, **kwargs: _response(500, json.dumps({'message': 'boom'})))

    with pytest.raises(RuntimeError, match='Server responded with 500: boom'):
        Client(gcd_nop_project).delete_job()


def test_post_error_without_json_body(gcd_nop_project, monkeypatch):
    '''A non-JSON error body is reported as it came'''
    monkeypatch.setattr(requests, 'post',
                        lambda url, **kwargs: _response(502, 'Bad Gateway'))

    with pytest.raises(RuntimeError, match='Server responded with 502: Bad Gateway'):
        Client(gcd_nop_project).delete_job()


###########################
# Configuration
###########################

def test_print_configuration(gcd_nop_project, scserver_credential, caplog):
    '''The configuration the client would use is reportable'''
    creds = scserver_credential(8000, username='user', password='pass')
    gcd_nop_project.set('option', 'credentials', creds)

    client = Client(gcd_nop_project)
    client.configure_whitelist(add=['.'])
    client.print_configuration()

    assert 'Username: user' in caplog.text
    assert 'Directory whitelist:' in caplog.text
    assert os.path.abspath('.') in caplog.text


def test_configure_whitelist_add_and_remove(gcd_nop_project, scserver_credential):
    '''Whitelist entries are added once and can be taken back out'''
    creds = scserver_credential(8000)
    gcd_nop_project.set('option', 'credentials', creds)

    client = Client(gcd_nop_project)
    client.configure_whitelist(add=['.', '.'])

    with open(creds) as f:
        assert json.load(f)['directory_whitelist'] == [os.path.abspath('.')]

    client.configure_whitelist(remove=['.', 'neverlisted'])

    with open(creds) as f:
        assert json.load(f)['directory_whitelist'] == []
