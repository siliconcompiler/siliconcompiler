import json
import os

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import call, login, outcome, slug                         # noqa: E402
from test_server_jobs import FakeDispatcher, create, stage, submit      # noqa: E402
from test_server_sources_flow import wait_for                          # noqa: E402


# A run that starts part-way through its flow (surface D175): the results of a
# node it reads and does not run come from the upload, or from the earlier job
# named in `continues_from` -- copied in while staging.


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def me(server_client, key, token):
    return call(server_client, key, "GET", "/v1/me", token).get_json()["id"]


def ran(server, user_id, nodes=(("stepone", "0"),), resources=()):
    '''An earlier job that ran ``nodes``, its results indexed as a run's are.'''
    from siliconcompiler.remote.server import artifacts
    from siliconcompiler.remote.server.ids import uuid7

    store, jobs = server.config["SC_STORE"], server.config["SC_JOBS"]
    job_id = str(uuid7())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, manifest_pdk, "
        "  manifest_resources) VALUES (?, ?, 'completed', 'gcd', 'earlier', '{}', 'none', ?)",
        (job_id, user_id, json.dumps([list(pair) for pair in resources])))
    job = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    root = jobs.job_root(user_id, job_id)
    for step, index in nodes:
        store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                      "VALUES (?, ?, ?, 'completed')", (job_id, step, index))
        node = root / "gcd" / "earlier" / step / index
        (node / "outputs").mkdir(parents=True)
        (node / "outputs" / "gcd.vg").write_text(f"module gcd; endmodule // from {step}\n")
        (node / "outputs" / "gcd.pkg.json").write_text(json.dumps({"from": job_id}))
        (node / f"sc_{step}_{index}.log").write_text("ran\n")
        artifacts.collect_node(store, server.config["SC_STORAGE"], server.config["SC_CONFIG"],
                               job, root, step, index)
    return job_id


def entry(job_id, step="stepone"):
    return {"step": step, "index": "0", "job_id": job_id}


def from_steptwo(project):
    project.option.add_from("steptwo")
    return project


###########################
# Create
###########################

def test_an_entry_is_recorded_and_echoed(server, server_client, key, token, me):
    earlier = ran(server, me)

    response = create(server_client, key, token, continues_from=[entry(earlier)])

    assert response.status_code == 201, response.get_json()
    assert response.get_json()["continues_from"] == [entry(earlier)]
    rows = server.config["SC_STORE"].all("SELECT * FROM job_continuations WHERE job_id = ?",
                                         (response.get_json()["id"],))
    assert [(row["step"], row["from_job_id"]) for row in rows] == [("stepone", earlier)]
    # And absent where the run continues from nothing.
    assert "continues_from" not in create(server_client, key, token,
                                          jobname="job1").get_json()


@pytest.mark.parametrize("value", [
    {"step": "stepone"},                                   # not a list
    [{"step": "stepone", "index": "0"}],                   # a member missing
    [{"step": "stepone", "index": "0", "job_id": "not-a-job-id"}],
    [{"step": "stepone", "index": "0", "job_id": "01a0e000-0000-7000-8000-000000000001",
      "extra": 1}],
    # The old spelling of the member is an unknown member now.
    [{"step": "stepone", "index": "0", "job": "01a0e000-0000-7000-8000-000000000001"}],
])
def test_a_malformed_list_is_invalid(server_client, key, token, value):
    response = create(server_client, key, token, continues_from=value)

    assert (response.status_code, slug(response)) == (400, "invalid-request")


def test_two_entries_for_one_node_are_invalid(server, server_client, key, token, me):
    earlier = ran(server, me)

    response = create(server_client, key, token,
                      continues_from=[entry(earlier), entry(earlier)])

    assert (response.status_code, slug(response)) == (400, "invalid-request")


def refused(response):
    assert response.status_code == 422, response.get_json()
    assert slug(response) == "prior-results-unavailable"
    return response.get_json()["reason"]


def test_anothers_job_and_no_job_are_the_same_answer(server, server_client, key, token):
    '''🔴 It confirms nothing.'''
    from siliconcompiler.remote import dpop

    other_key = dpop.generate_key()
    other_token = login(server_client, other_key, subject="machine:1001").get_json()[
        "access_token"]
    theirs = ran(server, call(server_client, other_key, "GET", "/v1/me",
                              other_token).get_json()["id"])

    first = create(server_client, key, token, continues_from=[entry(theirs)])
    second = create(server_client, key, token,
                    continues_from=[entry("01a0e000-0000-7000-8000-000000000001")])

    assert refused(first) == refused(second) == "not_found"
    assert first.get_json()["detail"].replace(theirs, "") == \
        second.get_json()["detail"].replace("01a0e000-0000-7000-8000-000000000001", "")


def test_an_archived_job_may_be_continued_from(server, server_client, key, token, me):
    '''🔴 An explicit `-from` may name an archived job: `archived` is registered
    and never raised.'''
    earlier = ran(server, me)
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET archived_at = '2026-09-01T00:00:00.000Z', archived_by = ? "
        "WHERE id = ?", (me, earlier))

    response = create(server_client, key, token, continues_from=[entry(earlier)])

    assert response.status_code == 201, response.get_json()


def test_a_node_the_job_did_not_run_is_not_completed(server, server_client, key, token, me):
    earlier = ran(server, me)

    assert refused(create(server_client, key, token,
                          continues_from=[entry(earlier, step="steptwo")])) == "not_completed"


@pytest.mark.parametrize("column,value", [
    ("deleted_at = '2026-09-01T00:00:00.000Z', delete_reason = 'retention lapsed'", "expired"),
    ("withheld_at = '2026-09-01T00:00:00.000Z', withheld_by = ?", "withheld"),
])
def test_results_gone_or_withheld_cannot_be_used(server, server_client, key, token, me,
                                                 column, value):
    earlier = ran(server, me)
    params = (me, earlier) if "?" in column else (earlier,)
    server.config["SC_STORE"].execute(
        f"UPDATE artifacts SET {column} WHERE job_id = ? AND kind = 'node'", params)

    assert refused(create(server_client, key, token,
                          continues_from=[entry(earlier)])) == value


def test_results_built_on_what_nobody_may_use_are_refused(server, server_client, key,
                                                          token, me):
    '''🔴 The job's resource set includes what it copies: without it a job
    could continue from results built on a PDK the caller may not use.'''
    earlier = ran(server, me, resources=[("pdk", "secret130")])
    server.config["SC_CONFIG"]._values["denied_resources"] = {"pdk": ["secret*"]}

    response = create(server_client, key, token, continues_from=[entry(earlier)])

    assert (response.status_code, slug(response)) == (403, "entitlement-denied")
    assert response.get_json()["resource"] == "secret130"


###########################
# Submit, and the copy
###########################

def submitted(server_client, key, token, archive, **body):
    path, digest, size = archive
    job = stage(server_client, key, token, path, size, **body)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


def test_the_results_are_copied_in_while_staging(server, server_client, key, token, me,
                                                 job_archive, nop_project, dispatcher):
    earlier = ran(server, me)

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier)])

    assert response.status_code == 202, response.get_json()
    assert response.get_json()["state"] == "staging"      # a copy always stages
    assert wait_for(lambda: dispatcher.submitted)

    outputs = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0" / \
        "stepone" / "0" / "outputs"
    assert (outputs / "gcd.vg").read_text() == "module gcd; endmodule // from stepone\n"
    assert json.loads((outputs / "gcd.pkg.json").read_text()) == {"from": earlier}
    # 🔴 The copied node is no node of this job's.
    assert [row["step"] for row in server.config["SC_STORE"].all(
        "SELECT step FROM job_nodes WHERE job_id = ?", (job["id"],))] == ["steptwo"]


def test_a_node_in_the_upload_is_taken_from_it(server, server_client, key, token, me,
                                               job_archive, nop_project, dispatcher):
    '''In both: the upload's, so a file changed by hand is the one used, and
    nothing is copied -- so nothing stages.'''
    from siliconcompiler.utils.paths import workdir

    earlier = ran(server, me)
    outputs = os.path.join(workdir(nop_project, step="stepone", index="0"), "outputs")
    os.makedirs(outputs)
    with open(os.path.join(outputs, "gcd.vg"), "w") as f:
        f.write("module gcd; endmodule // mine\n")

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier)])

    assert response.status_code == 202, response.get_json()
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "queued"


def test_a_node_in_neither_is_a_missing_member(server_client, key, token, job_archive,
                                               nop_project, dispatcher):
    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)))

    assert response.status_code == 422
    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "missing_member")
    assert "stepone/0" in response.get_json()["detail"]
    assert not dispatcher.submitted


def test_a_node_only_copied_in_cannot_be_named_again(server, server_client, key, token, me,
                                                     job_archive, nop_project, dispatcher):
    '''A chain: B continues from A, and C names B for a node B only copied --
    which B did not run.'''
    earlier = ran(server, me)
    b, _ = submitted(server_client, key, token, job_archive(from_steptwo(nop_project)),
                     continues_from=[entry(earlier)])
    assert wait_for(lambda: dispatcher.submitted)

    assert refused(create(server_client, key, token, jobname="job1",
                          continues_from=[entry(b["id"])])) == "not_completed"


def test_results_gone_before_the_copy_reject_the_job(server, server_client, key, token, me,
                                                     job_archive, nop_project, dispatcher,
                                                     monkeypatch):
    from siliconcompiler.remote.server import jobs

    earlier = ran(server, me)

    def gone(archive, target):
        raise FileNotFoundError(archive)
    monkeypatch.setattr(jobs, "_extract_outputs", gone)

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier)])

    # Found while staging, so it arrives on the job.
    assert refused(response) == "expired"
    store = server.config["SC_STORE"]
    assert store.one("SELECT state FROM jobs WHERE id = ?",
                     (job["id"],))["state"] == "rejected"
    assert not dispatcher.submitted


def test_results_withheld_before_the_copy_reject_the_job(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher,
        monkeypatch):
    '''🔴 The copy re-checks withholding: an administrator who withheld the
    earlier results after submit stops them being used.'''
    from siliconcompiler.remote.server.jobs import JobService

    earlier = ran(server, me)
    real = JobService._account_upstream

    def withheld_meanwhile(self, *args, **kwargs):
        found = real(self, *args, **kwargs)
        self._store.execute("UPDATE artifacts SET withheld_at = '2026-09-28T00:00:00.000Z', "
                            "withheld_by = ? WHERE job_id = ? AND kind = 'node'",
                            (me, earlier))
        return found
    monkeypatch.setattr(JobService, "_account_upstream", withheld_meanwhile)

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier)])

    assert refused(response) == "withheld"
    assert response.get_json()["job_id"] == earlier
    assert server.config["SC_STORE"].one("SELECT state FROM jobs WHERE id = ?",
                                         (job["id"],))["state"] == "rejected"
    assert not dispatcher.submitted


def test_a_store_that_does_not_answer_the_copy_is_the_servers_failure(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher,
        monkeypatch):
    from siliconcompiler.remote.server import jobs

    earlier = ran(server, me)

    def no_answer(archive, target):
        raise OSError(5, "Input/output error")
    monkeypatch.setattr(jobs, "_extract_outputs", no_answer)

    job, _ = submitted(server_client, key, token, job_archive(from_steptwo(nop_project)),
                       continues_from=[entry(earlier)])

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("/staging-failed")
    assert not dispatcher.submitted


def test_a_submit_rechecks_what_create_accepted(server, server_client, key, token, me,
                                                job_archive, nop_project, dispatcher):
    '''Its artifacts can be deleted between the two.'''
    earlier = ran(server, me)
    archive, digest, size = job_archive(from_steptwo(nop_project))
    job = stage(server_client, key, token, archive, size, continues_from=[entry(earlier)])
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET deleted_at = '2026-09-01T00:00:00.000Z', deleted_by = ? "
        "WHERE id = ?", (me, earlier))

    assert refused(outcome(server_client, key, token,
                           submit(server_client, key, token, job["id"], digest, size))) \
        == "deleted"


def test_a_skipped_upstream_node_is_looked_through(server, server_client, key, token, me,
                                                   job_archive, nop_project, dispatcher):
    '''A node the earlier job skipped has no results and is not
    `not_completed`: the run reads what fed it -- here nothing.'''
    earlier = ran(server, me)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'skipped' WHERE job_id = ?", (earlier,))

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier)])

    assert response.status_code == 202, response.get_json()
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "queued"
