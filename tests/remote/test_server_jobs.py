import json
import os
import tarfile
import threading

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server import config  # noqa: E402
from siliconcompiler.remote.server.running import runspec  # noqa: E402
from siliconcompiler.remote.server.staging.archive import ArchiveRejected, extract  # noqa: E402

from conftest import raw_archive, settle, slug, upload, write_progress  # noqa: E402


LIMITS = {"max_archive_members": 100, "max_archive_expanded_bytes": 1 << 20}


def get(api, job):
    return api("GET", f"/v1/jobs/{job['id']}").get_json()


def test_a_job_goes_from_create_to_completed(server, api, dispatcher, submit):
    job = submit()

    assert job["state"] == "queued", job["error"]
    assert [t["state"] for t in job["transitions"]] == ["created", "staging", "queued"]
    assert (job["design"], job["flow"], job["terminal"]) == ("gcd", "nopflow", False)
    assert [(n["step"], n["state"]) for n in job["nodes"]] == [("stepone", "pending"),
                                                               ("steptwo", "pending")]
    assert dispatcher.submitted == [job["id"]]

    root = server.config["SC_JOBS"].root(job["owner"]["id"], job["id"])
    run = json.loads((root / runspec.RUN_FILENAME).read_text())
    assert run["builddir"] == str(root) and run["cachedir"] == str(root.parents[3] / "cache")
    assert (root / "gcd" / "job0" / "gcd.pkg.json").is_file()
    assert not server.config["SC_JOBS"].storage.upload_path(job["id"]).exists()

    write_progress(server, job, "running", {"stepone/0": "running", "steptwo/0": "pending"})
    running = api("GET", f"/v1/jobs/{job['id']}")
    assert running.get_json()["state"] == "running"
    assert running.headers["Retry-After"] == "1"
    assert running.get_json()["nodes"][0]["terminal"] is False

    write_progress(server, job, "completed", finished_at=1010.0)
    dispatcher.alive = False
    done = api("GET", f"/v1/jobs/{job['id']}")
    assert "Retry-After" not in done.headers
    done = done.get_json()
    assert (done["state"], done["terminal"], done["error"]) == ("completed", True, None)
    assert done["progress"] == {"total_count": 2, "completed_count": 2, "failed_count": 0,
                                "skipped_count": 0, "cancelled_count": 0}
    assert done["finished_at"] == "1970-01-01T00:16:50Z"
    assert (root / "gcd" / "job0" / "gcd.pkg.json").is_file()


@pytest.mark.parametrize("progress, alive, state, error, detail", [
    (("failed", {"stepone/0": "failed", "steptwo/0": "cancelled"}, {"error": "boom"}), False,
     "failed", "run-failed", "boom"),
    (("completed", {"stepone/0": "completed", "steptwo/0": "failed"}, {}), False,
     "failed", "run-failed", "a node failed"),
    (("running", {"stepone/0": "running", "steptwo/0": "pending"}, {}), False,
     "failed", "run-interrupted", "the run ended without finishing"),
    (None, False, "failed", "run-interrupted", "the run ended without finishing"),
    (("running", {"stepone/0": "running", "steptwo/0": "pending"}, {}), True,
     "running", None, None),
])
def test_a_job_follows_what_its_run_reports(server, api, dispatcher, submit, progress, alive,
                                            state, error, detail):
    '''A run that is gone without finishing fails the job, with its nodes closed.'''
    job = submit()
    if progress:
        write_progress(server, job, progress[0], progress[1], **progress[2])
    dispatcher.alive = alive

    after = get(api, job)

    assert after["state"] == state
    assert (after["error"] or {}).get("type", "").rsplit("/", 1)[-1] == (error or "")
    assert (after["error"] or {}).get("detail") == detail
    assert all(n["terminal"] for n in after["nodes"]) == after["terminal"]


@pytest.mark.parametrize("method, path, body", [
    ("GET", "/v1/jobs/{id}", None),
    ("POST", "/v1/jobs/{id}/upload-grant", {"size_bytes": 1, "digest": "sha256:" + "0" * 64}),
    ("POST", "/v1/jobs/{id}/submit", {}),
    ("POST", "/v1/jobs/{id}/cancel", {"reason": "mine"}),
    ("DELETE", "/v1/jobs/{id}", None),
])
def test_another_users_job_is_not_found(api, stranger, method, path, body):
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()

    response = stranger(method, path.format(id=job["id"]), json=body)

    assert response.status_code == 404 and slug(response) == "not-found"
    assert stranger("GET", "/v1/jobs").get_json() == {"items": []}
    assert api("GET", f"/v1/jobs/{job['id']}").get_json()["state"] == "created"


@pytest.mark.parametrize("body, status, expected", [
    ({"design": "gcd", "jobname": "j", "continues_from": [
        {"step": "place", "index": "0", "job_id": "x"}]}, 422, "prior-results-unavailable"),
    ({"design": "gcd", "jobname": "j", "python_packages": {"requirements": ["numpy"]}},
     501, "feature-unsupported"),
    ({"design": "gcd", "jobname": "j", "descriptor": {"needs": ["jobs.reuse"]}},
     501, "feature-unsupported"),
    ({"jobname": "j"}, 400, "invalid-request"),
    ({"design": "../x", "jobname": "j"}, 400, "invalid-request"),
])
def test_a_create_the_server_cannot_serve_is_refused(api, body, status, expected):
    response = api("POST", "/v1/jobs", json=body)

    assert (response.status_code, slug(response)) == (status, expected)
    assert api("GET", "/v1/jobs").get_json() == {"items": []}


def test_create_with_the_same_key_is_the_same_job_and_listing_pages(api):
    body = {"design": "gcd", "jobname": "job0"}
    first = api("POST", "/v1/jobs", json=body, headers={"Idempotency-Key": "a"})
    again = api("POST", "/v1/jobs", json=body, headers={"Idempotency-Key": "a"})
    ids = [first.get_json()["id"]]
    ids += [api("POST", "/v1/jobs", json=body, headers={"Idempotency-Key": key}).get_json()["id"]
            for key in ("b", "c")]

    assert first.status_code == again.status_code == 201
    assert first.headers["Location"] == f"/v1/jobs/{ids[0]}"
    assert again.get_json()["id"] == ids[0]

    page = api("GET", "/v1/jobs?limit=2")
    link = page.headers["Link"]
    assert [j["id"] for j in page.get_json()["items"]] == ids[:0:-1]
    assert "nodes" not in page.get_json()["items"][0]
    assert link.startswith("</v1/jobs?limit=2&cursor=") and link.endswith('>; rel="next"')

    last = api("GET", link[1:link.index(">")])
    assert [j["id"] for j in last.get_json()["items"]] == ids[:1]
    assert "Link" not in last.headers
    assert slug(api("GET", "/v1/jobs?cursor=junk")) == "invalid-cursor"


@pytest.mark.parametrize("change, status, expected", [
    (lambda size, digest: {"size_bytes": size, "digest": "sha256:" + "1" * 64}, 409,
     "job-state-conflict"),
    (lambda size, digest: {"size_bytes": 1 << 40, "digest": digest}, 413, "upload-too-large"),
    (lambda size, digest: {"size_bytes": 0, "digest": digest}, 400, "invalid-request"),
    (lambda size, digest: {"size_bytes": size, "digest": "md5:ab"}, 400, "invalid-request"),
])
def test_a_grant_is_bound_to_its_size_and_digest(api, change, status, expected):
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    digest = "sha256:" + "0" * 64
    grant = api("POST", f"/v1/jobs/{job['id']}/upload-grant",
                json={"size_bytes": 10, "digest": digest})
    assert grant.get_json()["headers"] == {"content-length": "10"}
    assert api("POST", f"/v1/jobs/{job['id']}/upload-grant",
               json={"size_bytes": 10, "digest": digest}).status_code == 200

    response = api("POST", f"/v1/jobs/{job['id']}/upload-grant", json=change(10, digest))

    assert (response.status_code, slug(response)) == (status, expected)


@pytest.mark.parametrize("sent, tamper, status, expected", [
    (b"x" * 10, False, 204, ""),
    (b"x" * 11, False, 413, "upload-too-large"),
    (b"x" * 9, False, 400, "invalid-request"),
    (b"x" * 10, True, 400, "invalid-request"),
])
def test_the_signed_put_takes_what_the_grant_names(server_client, api, sent, tamper, status,
                                                   expected):
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    url = api("POST", f"/v1/jobs/{job['id']}/upload-grant",
              json={"size_bytes": 10, "digest": "sha256:" + "0" * 64}).get_json()["url"]
    path = url[len("http://localhost"):]

    response = server_client.put(path.replace("&sig=", "&sig=A") if tamper else path, data=sent)

    assert (response.status_code, slug(response)) == (status, expected)


def test_the_digest_is_checked_before_anything_is_extracted(server, server_client, api,
                                                            dispatcher, job_archive):
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    archive = job_archive()
    assert upload(server_client, api, job["id"], archive, sent=b"x" * archive[2]).status_code \
        == 204

    refused = api("POST", f"/v1/jobs/{job['id']}/submit", json={})

    assert (refused.status_code, slug(refused)) == (422, "upload-digest-mismatch")
    assert not (server.config["SC_DATADIR"] / "users").exists()
    assert get(api, job)["state"] == "created"

    assert upload(server_client, api, job["id"], archive).status_code == 204
    assert api("POST", f"/v1/jobs/{job['id']}/submit", json={}).status_code == 202


def test_a_job_with_no_upload_cannot_be_submitted(api):
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()

    assert slug(api("POST", f"/v1/jobs/{job['id']}/submit", json={})) == "job-state-conflict"


@pytest.mark.parametrize("kind, jobname, expected, reason", [
    ("no manifest", "job0", "archive-rejected", "missing_manifest"),
    ("not a tar", "job0", "archive-rejected", "invalid_manifest"),
    ("twice", "job0", "archive-rejected", "traversal"),
    ("another jobname", "other", "declared-mismatch", None),
    ("newer schema", "job0", "software-unavailable", "unavailable"),
])
def test_a_refused_archive_ends_the_job_rejected(server, api, dispatcher, submit, job_archive,
                                                 monkeypatch, kind, jobname, expected, reason):
    '''Staging refuses on what the archive holds, and leaves no tree behind.'''
    archive = {
        "no manifest": lambda: raw_archive({"readme": b"x"}),
        "not a tar": lambda: raw_archive({}) and _not_a_tar(),
        "twice": lambda: job_archive(extra={"gcd.pkg.json": b"{}"}),
        "another jobname": job_archive,
        "newer schema": job_archive,
    }[kind]()
    if kind == "newer schema":
        monkeypatch.setattr("siliconcompiler.remote.server.jobs.SCHEMA_VERSION", "0.0.1")

    job = submit(archive, jobname=jobname)

    assert job["state"] == "rejected" and job["terminal"]
    assert job["error"]["type"].rsplit("/", 1)[-1] == expected
    assert job["error"].get("reason") == reason
    assert not dispatcher.submitted
    assert not server.config["SC_JOBS"].root(job["owner"]["id"], job["id"]).exists()


def _not_a_tar():
    import hashlib

    with open("raw.tar.gz", "wb") as f:
        f.write(b"this is not an archive" * 10)
    return os.path.abspath("raw.tar.gz"), "sha256:" + hashlib.sha256(
        b"this is not an archive" * 10).hexdigest(), 220


def _tar(*members):
    '''Members as ``(name, type, content_or_linkname)``, in this order.'''
    import io

    with tarfile.open("odd.tar", "w") as tar:
        for name, kind, content in members:
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                info.linkname = content
            elif kind == tarfile.REGTYPE:
                info.size = len(content)
            tar.addfile(info, io.BytesIO(content) if kind == tarfile.REGTYPE else None)
    return "odd.tar"


FILE, DIR, SYM, LNK = tarfile.REGTYPE, tarfile.DIRTYPE, tarfile.SYMTYPE, tarfile.LNKTYPE


@pytest.mark.parametrize("members, reason", [
    ([("../x", FILE, b"x")], "traversal"),
    ([("/etc/x", FILE, b"x")], "traversal"),
    ([("a", FILE, b"x"), ("a", FILE, b"y")], "traversal"),
    ([("l", SYM, "a"), ("l/b", FILE, b"x")], "traversal"),
    ([("l", SYM, "../out")], "link_member"),
    ([("l", SYM, "/etc/passwd")], "link_member"),
    ([("l", LNK, "missing")], "link_member"),
    ([("p", tarfile.FIFOTYPE, b"")], "device_member"),
    ([("a", DIR, b""), ("a", FILE, b"x")], "invalid_manifest"),
    ([("a", FILE, b"x"), ("a", DIR, b"")], "invalid_manifest"),
    ([("a", FILE, b"x"), ("a/b", FILE, b"x")], "invalid_manifest"),
    ([("a", FILE, b"x"), ("b", FILE, b"x"), ("c", FILE, b"x")], "member_count"),
    ([("a", FILE, b"x" * 100)], "expanded_bytes"),
])
def test_extraction_refuses_what_breaks_a_rule(members, reason):
    '''A member landing on an existing file or directory is refused, not an OSError.'''
    limits = {"max_archive_members": 2, "max_archive_expanded_bytes": 50}
    big = {"member_count": 2, "expanded_bytes": 50}

    with pytest.raises(ArchiveRejected) as refused:
        extract(_tar(*members), "out", {**LIMITS, **limits} if reason in big else LIMITS)

    assert refused.value.reason == reason


def test_extraction_keeps_links_that_stay_inside():
    extract(_tar(("d", DIR, b""), ("d/a", FILE, b"x"), ("s", SYM, "d/a"), ("h", LNK, "d/a")),
            "out", LIMITS)

    assert open("out/s").read() == open("out/h").read() == "x"


def test_a_cancel_during_staging_stops_the_job(api, dispatcher, submit):
    dispatcher.gate.clear()
    job = submit(settled=False)
    assert dispatcher.entered.wait(10)

    cancelled = api("POST", f"/v1/jobs/{job['id']}/cancel", json={"reason": "stop"})
    assert (cancelled.status_code, cancelled.get_json()["state"]) == (202, "cancelling")
    dispatcher.gate.set()

    job = settle(api, job["id"], ("staging", "cancelling"))
    assert job["state"] == "cancelled" and job["terminal"]
    assert [t.get("reason") for t in job["transitions"]][-2:] == ["stop", "stop"]
    assert len(dispatcher.cancelled) == 1
    assert all(n["state"] == "cancelled" for n in job["nodes"])


def test_a_cancel_while_running_stops_the_run_and_is_idempotent(server, api, dispatcher, submit):
    job = submit()
    write_progress(server, job, "running", {"stepone/0": "running", "steptwo/0": "pending"})
    assert get(api, job)["state"] == "running"

    first = api("POST", f"/v1/jobs/{job['id']}/cancel", json={})
    assert first.get_json()["state"] == "cancelling"
    assert dispatcher.cancelled == [f"fake:{job['id']}"]

    after = get(api, job)
    again = api("POST", f"/v1/jobs/{job['id']}/cancel", json={})
    assert (after["state"], again.status_code, again.get_json()["state"]) \
        == ("cancelled", 202, "cancelled")
    assert [n["state"] for n in after["nodes"]] == ["cancelled", "cancelled"]
    assert len(after["transitions"]) == 6


@pytest.mark.parametrize("reason", ["x" * 301, "two\nlines"])
def test_a_cancel_reason_is_one_short_line(api, reason):
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()

    assert slug(api("POST", f"/v1/jobs/{job['id']}/cancel", json={"reason": reason})) \
        == "invalid-request"
    assert api("POST", f"/v1/jobs/{job['id']}/cancel").get_json()["state"] == "cancelled"


def test_only_a_finished_job_is_deleted_and_it_stays_readable(server, api, dispatcher, submit):
    job = submit()
    root = server.config["SC_JOBS"].root(job["owner"]["id"], job["id"])

    refused = api("DELETE", f"/v1/jobs/{job['id']}")
    assert (refused.status_code, slug(refused)) == (409, "job-state-conflict")
    assert root.exists()

    api("POST", f"/v1/jobs/{job['id']}/cancel")
    get(api, job)
    assert [api("DELETE", f"/v1/jobs/{job['id']}").status_code for _ in range(2)] == [204, 204]

    after = get(api, job)
    assert after["state"] == "cancelled" and after["deleted_at"]
    assert not root.exists()
    assert api("GET", "/v1/jobs").get_json() == {"items": []}


def test_the_concurrent_cap_is_refused_as_a_wait(monkeypatch, api, dispatcher, submit,
                                                 server_client, job_archive):
    monkeypatch.setitem(config.LIMITS, "concurrent_jobs", 1)
    first = submit()
    second = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    assert upload(server_client, api, second["id"], job_archive()).status_code == 204

    refused = api("POST", f"/v1/jobs/{second['id']}/submit", json={})

    assert (refused.status_code, slug(refused)) == (429, "limit-exceeded")
    assert refused.get_json()["limit"] == "concurrent_jobs"
    assert refused.headers["Retry-After"]
    assert get(api, second)["state"] == "created"

    api("POST", f"/v1/jobs/{first['id']}/cancel")
    get(api, first)
    assert api("POST", f"/v1/jobs/{second['id']}/submit", json={}).status_code == 202


def test_two_moves_cannot_both_pass_the_concurrent_cap(server, api):
    '''The count and the move are one transaction: simultaneous submits admit one.'''
    from siliconcompiler.remote.server.errors import ProblemError

    jobs = server.config["SC_JOBS"]
    ids = [api("POST", "/v1/jobs", json={"design": "gcd", "jobname": f"job{n}"}).get_json()["id"]
           for n in range(2)]
    start, outcomes = threading.Barrier(2), []

    def submit(job_id):
        start.wait()
        try:
            outcomes.append(jobs.move(job_id, ("created",), "staging", cap=1))
        except ProblemError as e:
            outcomes.append(e.error.slug)
        finally:
            jobs.store.release()

    threads = [threading.Thread(target=submit, args=(job_id,)) for job_id in ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(map(str, outcomes)) == ["True", "limit-exceeded"]
    states = sorted(jobs.row(job_id)["state"] for job_id in ids)
    assert states == ["created", "staging"]


@pytest.mark.parametrize("since, state", [
    (None, "abandoned"), ("submit", "created"), ("receiving", "created"),
], ids=["idle", "waiting-for-a-slot", "uploading"])
def test_a_job_idle_past_the_limit_is_abandoned_and_its_upload_discarded(
        monkeypatch, server, server_client, api, job_archive, since, state):
    '''Idle since the client's last call, not old: a submit waiting for a slot and an
    upload still arriving keep the job.'''
    monkeypatch.setitem(config.LIMITS, "concurrent_jobs", 0)
    jobs = server.config["SC_JOBS"]
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    assert upload(server_client, api, job["id"], job_archive()).status_code == 204
    jobs.store.execute("UPDATE jobs SET created_at = created_at - 1000, "
                       "active_at = active_at - 1000 WHERE id = ?", (job["id"],))

    if since == "submit":
        assert slug(api("POST", f"/v1/jobs/{job['id']}/submit", json={})) == "limit-exceeded"
    elif since == "receiving":
        monkeypatch.setattr(jobs, "_receiving", {job["id"]})

    assert get(api, job)["state"] == state
    assert jobs.storage.upload_path(job["id"]).exists() == (state == "created")


def test_two_threads_cannot_both_move_a_job(server, api):
    '''`move` is conditional on the state it leaves: one wins, one transition is recorded.'''
    job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    jobs = server.config["SC_JOBS"]
    barrier, won = threading.Barrier(8), []

    def race():
        barrier.wait()
        won.append(jobs.move(job["id"], ("created",), "staging"))
        jobs.store.release()

    threads = [threading.Thread(target=race) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(won) == [False] * 7 + [True]
    assert [row["state"] for row in jobs.store.all(
        "SELECT state FROM job_transitions WHERE job_id = ? ORDER BY rowid", (job["id"],))] \
        == ["created", "staging"]


@pytest.mark.timeout(90)
def test_a_nop_run_goes_through_the_real_dispatcher(server, api, submit):
    job = settle(api, submit()["id"], ("staging", "queued", "running"))

    assert job["state"] == "completed", job["error"]
    assert [n["state"] for n in job["nodes"]] == ["completed", "completed"]
    assert job["started_at"] and job["finished_at"]
    root = server.config["SC_JOBS"].root(job["owner"]["id"], job["id"])
    assert (root / "gcd" / "job0" / "stepone" / "0" / "outputs").is_dir()


@pytest.mark.timeout(90)
def test_the_client_runs_a_nop_project_remotely(live_server, tmp_credentials, nop_project):
    '''The real client, over a socket, to a completed job. Results come from the
    artifact endpoints, which the next step adds.'''
    from siliconcompiler.remote import Client

    tmp_credentials.set_server(live_server)
    nop_project.option.set_credentials(str(tmp_credentials.path))
    nop_project.option.set_remote(True)

    history = nop_project.run()

    job, _ = Client(tmp_credentials).job(history.get("record", "remoteid"))
    assert (job["state"], job["design"]) == ("completed", "gcd")
