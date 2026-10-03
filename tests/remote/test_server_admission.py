import threading

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import call, slug                                         # noqa: E402
from test_server_jobs import create, stage, submit                      # noqa: E402

from siliconcompiler.remote.server.errors import ProblemError           # noqa: E402


# `pending_uploads` and `concurrent_jobs` are optional hard ceilings: `null`
# where not enforced, and otherwise never exceeded however many requests
# arrive at once -- the count and the write it decides are one transaction
# (`BEGIN IMMEDIATE`).


def session_of(server_client, key, token):
    from siliconcompiler.remote.server.identity.auth import SCOPES, Session

    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    return Session(user_id=me, scope=" ".join(SCOPES), family_id=None, device_id=None,
                   jkt=None)


def all_at_once(store, count, work):
    '''``work(n)`` on ``count`` threads, and what each returned or raised.'''
    results = [None] * count

    def run(n):
        try:
            results[n] = work(n)
        except Exception as e:                                   # noqa: BLE001
            results[n] = e
        finally:
            store.release()

    threads = [threading.Thread(target=run, args=(n,)) for n in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    return results


def through_the_early_check_together(monkeypatch, name, count):
    '''Every request past the early, unlocked check before any admits: the
    race a count read outside the admitting transaction loses.'''
    from siliconcompiler.remote.server.jobs import JobService

    barrier = threading.Barrier(count)
    real = getattr(JobService, name)

    def check(self, user_id):
        if not self._store.connection.in_transaction:
            barrier.wait(timeout=30)
        return real(self, user_id)

    monkeypatch.setattr(JobService, name, check)


def test_an_unenforced_ceiling_is_null_and_admits_everything(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch):
    from siliconcompiler.remote.server.jobs import JobService

    limits = server.config["SC_CONFIG"].limits
    limits["pending_uploads"] = None
    limits["concurrent_jobs"] = None
    # Not about staging: a submitted job stays counted.
    monkeypatch.setattr(JobService, "_start_preparing", lambda self, job_id: None)

    published = server_client.get("/v1").get_json()["limits"]
    mine = call(server_client, key, "GET", "/v1/me", token).get_json()["limits"]
    for answer in (published, mine):
        assert answer["pending_uploads"] is None and answer["concurrent_jobs"] is None

    created = [create(server_client, key, token, jobname=f"job{n}") for n in range(12)]
    assert [response.status_code for response in created] == [201] * 12

    archive, digest, size = job_archive()
    for n in range(6):
        job = stage(server_client, key, token, archive, size, jobname=f"run{n}")
        assert submit(server_client, key, token, job["id"]).status_code == 202


def test_concurrent_creates_admit_only_the_pending_uploads_ceiling(
        server, server_client, key, token, monkeypatch):
    '''Eight at once against 3: three jobs, and five `429 limit-exceeded`.'''
    jobs = server.config["SC_JOBS"]
    server.config["SC_CONFIG"].limits["pending_uploads"] = 3
    session = session_of(server_client, key, token)
    through_the_early_check_together(monkeypatch, "_check_pending_uploads", 8)

    results = all_at_once(server.config["SC_STORE"], 8, lambda n: jobs.create(
        session, {"design": "gcd", "jobname": f"job{n}"}, None))

    admitted = [result for result in results if isinstance(result, tuple)]
    refused = [result for result in results if isinstance(result, ProblemError)]
    assert len(admitted) == 3 and len(refused) == 5, results
    assert {problem.error.slug for problem in refused} == {"limit-exceeded"}
    assert {problem.members["limit"] for problem in refused} == {"pending_uploads"}
    assert server.config["SC_STORE"].one(
        "SELECT count(*) AS n FROM jobs WHERE user_id = ? AND state = 'created'",
        (session.user_id,))["n"] == 3


def test_concurrent_jobs_is_checked_at_create(server, server_client, key, token):
    '''Before any upload. A create adds nothing to what this counts, so its
    race is at submit, below.'''
    store = server.config["SC_STORE"]
    server.config["SC_CONFIG"].limits["concurrent_jobs"] = 2
    for n, state in enumerate(("running", "queued")):
        job = create(server_client, key, token, jobname=f"active{n}").get_json()["id"]
        store.execute("UPDATE jobs SET state = ?, manifest_pdk = 'none' WHERE id = ?",
                      (state, job))

    refused = create(server_client, key, token, jobname="more")

    assert (refused.status_code, slug(refused)) == (429, "limit-exceeded")
    assert refused.get_json()["limit"] == "concurrent_jobs"
    assert refused.headers["Retry-After"]


def test_concurrent_submits_admit_only_the_concurrent_jobs_ceiling(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch):
    '''Five at once against 2: two go to `staging`, which the ceiling counts,
    and three are refused, staying `awaiting_input` with their uploads kept.'''
    from siliconcompiler.remote.server.jobs import JobService

    jobs = server.config["SC_JOBS"]
    store = server.config["SC_STORE"]
    server.config["SC_CONFIG"].limits["concurrent_jobs"] = 2
    monkeypatch.setattr(JobService, "_start_preparing", lambda self, job_id: None)
    session = session_of(server_client, key, token)

    archive, digest, size = job_archive()
    staged = [stage(server_client, key, token, archive, size, jobname=f"job{n}")["id"]
              for n in range(5)]
    through_the_early_check_together(monkeypatch, "_check_concurrent_jobs", 5)

    results = all_at_once(store, 5, lambda n: jobs.submit(session, staged[n], {}, None))

    admitted = [result for result in results if isinstance(result, dict)]
    refused = [result for result in results if isinstance(result, ProblemError)]
    assert len(admitted) == 2 and len(refused) == 3, results
    assert {problem.members["limit"] for problem in refused} == {"concurrent_jobs"}
    states = {job_id: store.one("SELECT state FROM jobs WHERE id = ?", (job_id,))["state"]
              for job_id in staged}
    assert sorted(states.values()) == ["awaiting_input"] * 3 + ["staging"] * 2
    for job_id, state in states.items():
        if state == "awaiting_input":
            assert jobs._storage.stat_upload(job_id) is not None
