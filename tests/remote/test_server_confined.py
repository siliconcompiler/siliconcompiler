import sys

import pytest

import test_logs

from conftest import call
from test_logs import finish, frames, stream_url

# The running-node fixture, shared rather than copied.
running = test_logs.running


pytest.importorskip("flask", reason="the server extra is not installed")
pytestmark = pytest.mark.skipif(sys.platform == "win32",
                                reason="creating links needs privileges on Windows")


# Every read the server makes of a job's tree, given a link a node's own code
# planted there (surface D133): none may show the caller the host's files.

SECRET = "the host's own file\n"


@pytest.fixture
def secret(tmp_path):
    path = tmp_path / "host-secret"
    path.write_text(SECRET)
    return path


@pytest.fixture
def linked_log(running, secret):
    '''The running node's log, replaced by a link to the host's file.'''
    job_id, log = running
    log.unlink()
    log.symlink_to(secret)
    return job_id


def test_the_live_tail_does_not_follow_a_log_replaced_by_a_link(
        server, server_client, key, token, linked_log):
    target = stream_url(server_client, key, token, linked_log)
    finish(server, linked_log)
    parsed = frames(server_client.get(target))

    assert not any(event == "log" for event, _, _ in parsed)
    assert parsed[-1][0] == "end"


def test_the_job_stream_does_not_follow_one_either(
        server, server_client, key, token, linked_log):
    response = call(server_client, key, "GET", f"/v1/jobs/{linked_log}/logs", token)
    target = response.headers["Location"].split("http://localhost", 1)[1]
    finish(server, linked_log)
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET state = 'completed' WHERE id = ?", (linked_log,))

    assert SECRET.strip() not in server_client.get(target).get_data(as_text=True)


def test_the_portal_does_not_show_a_log_through_a_link(
        server, server_client, key, token, running, secret):
    job_id, log = running
    (log.parent / "place.log").symlink_to(secret)

    response = call(server_client, key, "POST", "/v1/auth/browser", token, json={})
    server_client.get(response.get_json()["url"].split("http://localhost", 1)[1])
    page = server_client.get(f"/portal/jobs/{job_id}/logs/place/0?file=place.log")

    assert page.status_code == 200
    assert SECRET.strip() not in page.get_data(as_text=True)
    assert "could not be read" in page.get_data(as_text=True)


def test_a_progress_file_replaced_by_a_link_is_not_read(tmp_path):
    '''The run writes it inside the job's tree, and the server publishes it.'''
    import json

    from siliconcompiler.remote.server.running import runspec

    root = tmp_path / "job"
    root.mkdir()
    real = tmp_path / "elsewhere.json"
    real.write_text(json.dumps({"state": "completed"}))
    (root / runspec.PROGRESS_FILENAME).symlink_to(real)

    assert runspec.read_progress(root / runspec.PROGRESS_FILENAME, root) is None
    assert runspec.read_progress(real, tmp_path) == {"state": "completed"}
