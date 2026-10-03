import json
import time

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

import test_logs                                                        # noqa: E402

from conftest import call, login, slug                                  # noqa: E402
from test_logs import frames                                            # noqa: E402
from test_server_jobs import FakeDispatcher, stage, submit              # noqa: E402
from test_server_jobs import (                                          # noqa: E402,F401
    container_client, container_server, container_token, registry)

# The running-node fixture, shared rather than copied.
running = test_logs.running


# The server half of the v1 API's behaviour tests: the rules the rest of the
# suite does not hold.


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def job_read(client, key, token, job_id):
    return call(client, key, "GET", f"/v1/jobs/{job_id}", token).get_json()


def test_jobs_delete_gates_a_delete(server, server_client, key, job_archive, dispatcher):
    '''`jobs:write` keeps create, upload-grant, submit and cancel; a delete
    needs `jobs:delete`.'''
    narrow = login(server_client, key, scope="jobs:read jobs:write").get_json()
    assert "jobs:delete" not in narrow["scope"].split()
    token = narrow["access_token"]

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token, json={})

    response = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert (response.status_code, slug(response)) == (403, "insufficient-scope")
    assert 'scope="jobs:delete"' in response.headers["WWW-Authenticate"]


def test_a_staging_step_that_breaks_is_staging_failed(server, server_client, key, token,
                                                      job_archive, dispatcher, monkeypatch):
    '''The catch-all: `failed`, never `rejected`, and `detail` names only what failed.'''
    from siliconcompiler.remote.server.jobs import JobService

    def breaks(self, *args, **kwargs):
        raise RuntimeError("something internal")
    monkeypatch.setattr(JobService, "_account_upstream", breaks)

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    read = job_read(server_client, key, token, job["id"])
    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("/staging-failed")
    assert "something internal" not in json.dumps(read)
    assert not dispatcher.submitted


def test_an_image_that_will_not_unpack_is_staging_failed(  # noqa: F811
        container_server, container_client, key, container_token, job_archive,  # noqa: F811
        monkeypatch):
    from siliconcompiler.remote.server.software import images
    from test_server_jobs import wants

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake

    def will_not(root, ref, digest, mounts=()):
        raise RuntimeError("skopeo: manifest unknown")
    monkeypatch.setattr(images, "stage_bundle", will_not)

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                requested_versions=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    read = job_read(container_client, key, container_token, job["id"])
    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("/staging-failed")
    assert not fake.submitted


def test_a_stream_ends_when_its_capability_does(server, server_client, running):
    '''`end {"reason": "expired"}` at the URL's deadline, which is no later
    than the access token's: the client asks `/logs` again.'''
    job_id, log = running
    log.write_text("still going\n")
    expires = int(time.time()) + 2
    signature = server.config["SC_STORAGE"].sign_stream(job_id, "place", "0", expires, "n1")
    started = time.monotonic()

    events = frames(server_client.get(
        f"/stream/logs/{job_id}/place/0?expires={expires}&n=n1&sig={signature}"))

    assert events[-1][0] == "end" and events[-1][2] == {"reason": "expired"}
    assert time.monotonic() - started < 10
