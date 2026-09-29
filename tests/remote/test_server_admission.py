import threading

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import call, slug                                         # noqa: E402
from test_server_jobs import FakeDispatcher, create, stage              # noqa: E402

from siliconcompiler.remote.server.errors import ProblemError           # noqa: E402


# `pending_uploads` and `concurrent_jobs` are optional hard ceilings
# (entitlements §2): `null` where a deployment does not enforce one, and a
# numeric value that is never exceeded, however many requests arrive at once.
# The count and the write it decides are one transaction no other admission can
# interleave with (implementation-notes §3; SQLite's `BEGIN IMMEDIATE`).


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def session_of(server_client, key, token):
    from siliconcompiler.remote.server.auth import SCOPES, Session

    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    return Session(user_id=me, scope=" ".join(SCOPES), family_id=None, device_id=None,
                   jkt=None)


def all_at_once(count, work):
    '''``work(n)`` on ``count`` threads, and what each returned or raised.'''
    results = [None] * count

    def run(n):
        try:
            results[n] = work(n)
        except Exception as e:                                   # noqa: BLE001
            results[n] = e
        finally:
            server_store().release()

    threads = [threading.Thread(target=run, args=(n,)) for n in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    return results


_STORE = {}


def server_store():
    return _STORE["store"]


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


###########################
# null: not enforced, and published so
###########################

def test_an_unenforced_ceiling_is_null_and_admits_everything(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch):
    from siliconcompiler.remote.server.jobs import JobService

    limits = server.config["SC_CONFIG"].limits
    limits["pending_uploads"] = None
    limits["concurrent_jobs"] = None
    # Staging is not what this is about: a submitted job stays counted.
    monkeypatch.setattr(JobService, "_start_preparing", lambda self, job_id: None)

    published = server_client.get("/v1").get_json()["limits"]
    mine = call(server_client, key, "GET", "/v1/me", token).get_json()["limits"]
    assert published["pending_uploads"] is None and published["concurrent_jobs"] is None
    assert mine["pending_uploads"] is None and mine["concurrent_jobs"] is None

    created = [create(server_client, key, token, jobname=f"job{n}") for n in range(12)]
    assert [response.status_code for response in created] == [201] * 12

    from test_server_jobs import submit
    archive, digest, size = job_archive()
    for n in range(6):
        job = stage(server_client, key, token, archive, size, jobname=f"run{n}")
        assert submit(server_client, key, token, job["id"], digest, size).status_code == 202


###########################
# numeric: a hard ceiling under concurrent requests
###########################

def test_concurrent_creates_admit_only_the_pending_uploads_ceiling(
        server, server_client, key, token, monkeypatch):
    '''Eight creates at once against a `pending_uploads` of 3: three jobs, and
    five `429 limit-exceeded` naming the jobs that hold the slots.'''
    jobs = server.config["SC_JOBS"]
    _STORE["store"] = server.config["SC_STORE"]
    server.config["SC_CONFIG"].limits["pending_uploads"] = 3
    session = session_of(server_client, key, token)
    through_the_early_check_together(monkeypatch, "_check_pending_uploads", 8)

    results = all_at_once(8, lambda n: jobs.create(
        session, {"design": "gcd", "jobname": f"job{n}"}, None))

    admitted = [result for result in results if isinstance(result, tuple)]
    refused = [result for result in results if isinstance(result, ProblemError)]
    assert len(admitted) == 3 and len(refused) == 5, results
    assert {problem.error.slug for problem in refused} == {"limit-exceeded"}
    assert {problem.members["limit"] for problem in refused} == {"pending_uploads"}
    held = server.config["SC_STORE"].one(
        "SELECT count(*) AS n FROM jobs WHERE user_id = ? AND state = 'created'",
        (session.user_id,))["n"]
    assert held == 3


def test_concurrent_jobs_is_checked_at_create(server, server_client, key, token):
    '''Before any upload: at the ceiling, a create is `429`, naming it. A
    create adds nothing to what this counts, so the race it has is at submit,
    below.'''
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
    '''Five submits at once against a `concurrent_jobs` of 2: two jobs go to
    `staging`, which is what the ceiling counts, and three are refused and stay
    `awaiting_input` with their uploads kept, to be submitted again.'''
    from siliconcompiler.remote.server.jobs import JobService

    jobs = server.config["SC_JOBS"]
    store = _STORE["store"] = server.config["SC_STORE"]
    server.config["SC_CONFIG"].limits["concurrent_jobs"] = 2
    monkeypatch.setattr(JobService, "_start_preparing", lambda self, job_id: None)
    session = session_of(server_client, key, token)

    archive, digest, size = job_archive()
    staged = [stage(server_client, key, token, archive, size, jobname=f"job{n}")["id"]
              for n in range(5)]
    through_the_early_check_together(monkeypatch, "_check_concurrent_jobs", 5)

    results = all_at_once(5, lambda n: jobs.submit(session, staged[n], {"digest": digest},
                                                   None))

    admitted = [result for result in results if isinstance(result, dict)]
    refused = [result for result in results if isinstance(result, ProblemError)]
    assert len(admitted) == 2 and len(refused) == 3, results
    assert {problem.members["limit"] for problem in refused} == {"concurrent_jobs"}
    states = sorted(row["state"] for row in store.all(
        "SELECT state FROM jobs WHERE id IN (%s)" % ",".join("?" * 5), staged))
    assert states == ["awaiting_input"] * 3 + ["staging"] * 2
    for job_id in staged:
        if store.one("SELECT state FROM jobs WHERE id = ?", (job_id,))["state"] == \
                "awaiting_input":
            assert jobs._storage.stat_upload(job_id) is not None
