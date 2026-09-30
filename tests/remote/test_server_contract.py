import json
import time

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import call, login, slug                                  # noqa: E402
from test_server_jobs import FakeDispatcher, stage, submit              # noqa: E402
from test_server_jobs import (                                          # noqa: E402,F401
    container_client, container_server, container_token, registry)


# The server half of the contract's behaviour tests (contract.md §6), written
# so crucible can reuse them: the rules the rest of the suite does not already
# hold.


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def job_read(client, key, token, job_id):
    return call(client, key, "GET", f"/v1/jobs/{job_id}", token).get_json()


###########################
# Scopes
###########################

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


###########################
# Staging failures that are this server's
###########################

def test_a_staging_step_that_breaks_is_staging_failed(server, server_client, key, token,
                                                      job_archive, dispatcher, monkeypatch):
    '''The catch-all: this server's own failure, `failed` and never `rejected`,
    with `detail` naming only what failed.'''
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
                requires=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    read = job_read(container_client, key, container_token, job["id"])
    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("/staging-failed")
    assert not fake.submitted


###########################
# Logs
###########################

def test_a_stream_ends_when_its_capability_does(server, server_client, key, token):
    '''🔴 `end {"reason": "expired"}` at the URL's deadline, which is no later
    than the access token's: the client asks `/logs` again.'''
    from test_logs import frames

    import uuid

    store = server.config["SC_STORE"]
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    job_id = str(uuid.uuid4())
    store.execute("INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
                  "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
                  (job_id, me))
    store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                  "VALUES (?, 'place', '0', 'running')", (job_id,))
    row = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    log = server.config["SC_JOBS"].node_log_path(row, "place", "0")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("still going\n")

    storage = server.config["SC_STORAGE"]
    expires = int(time.time()) + 2
    signature = storage.sign_stream(job_id, "place", "0", expires, "n1")
    started = time.monotonic()
    response = server_client.get(
        f"/stream/logs/{job_id}/place/0?expires={expires}&n=n1&sig={signature}")

    events = frames(response)
    assert events[-1][0] == "end" and events[-1][2] == {"reason": "expired"}
    assert time.monotonic() - started < 10


###########################
# Behind a proxy that rewrites Host
###########################

def test_the_log_redirect_is_built_on_the_configured_origin(tmp_path):
    '''The stream `303`, like every URL handed out, is on the configured
    origin and never the `Host` a proxy wrote.'''
    from siliconcompiler.remote import dpop
    from siliconcompiler.remote.server.app import create_app
    import uuid

    datadir = tmp_path / "proxied"
    datadir.mkdir()
    (datadir / "config.json").write_text(json.dumps(
        {"public_origins": ["https://sc.example.test"]}))
    app = create_app(datadir)
    client = app.test_client()
    key = dpop.generate_key()
    backend = {"Host": "backend:8080"}
    public = "https://sc.example.test"

    token = client.post(
        "/v1/auth/token", data={"grant_type": "client_credentials",
                                "client_id": "local:machine:1000"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{public}/v1/auth/token"),
                 **backend},
        content_type="application/x-www-form-urlencoded").get_json()["access_token"]

    def authed(method, path):
        return client.open(path, method=method, headers={
            "Authorization": f"DPoP {token}", **backend,
            "DPoP": dpop.sign_proof(key, method, public + path.split("?")[0],
                                    access_token=token)})

    me = authed("GET", "/v1/me").get_json()["id"]
    store = app.config["SC_STORE"]
    job_id = str(uuid.uuid4())
    store.execute("INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
                  "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
                  (job_id, me))
    store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                  "VALUES (?, 'place', '0', 'running')", (job_id,))

    node = authed("GET", f"/v1/jobs/{job_id}/logs?step=place&index=0")
    whole = authed("GET", f"/v1/jobs/{job_id}/logs")

    assert node.status_code == 303, node.get_json()
    assert node.headers["Location"].startswith(f"{public}/stream/logs/{job_id}/place/0?")
    assert whole.headers["Location"].startswith(f"{public}/stream/logs/{job_id}?")
