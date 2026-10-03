import json
import os

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import call, outcome, read, slug, stranger                # noqa: E402
from test_server_jobs import create, stage, submit                      # noqa: E402
from test_server_sources_flow import wait_for                          # noqa: E402


# A run that starts part-way through its flow (surface D175): a node it reads
# and does not run comes from the upload, or from the earlier job named in
# `continues_from`, copied in while staging.

NO_JOB = "01a0e000-0000-7000-8000-000000000001"


def earlier(server, user_id, resources=()):
    '''A completed job's row, and the root its tree goes under.'''
    import uuid

    store = server.config["SC_STORE"]
    job_id = str(uuid.uuid4())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, manifest_pdk, "
        "  manifest_resources) VALUES (?, ?, 'completed', 'gcd', 'earlier', '{}', 'none', ?)",
        (job_id, user_id, json.dumps([list(pair) for pair in resources])))
    return (store.one("SELECT * FROM jobs WHERE id = ?", (job_id,)),
            server.config["SC_JOBS"].job_root(user_id, job_id))


def collect(server, job, root, step, index="0"):
    '''Record ``step`` as run, its results indexed as a run's are.'''
    from siliconcompiler.remote.server.outputs import artifacts

    server.config["SC_STORE"].execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                                      "VALUES (?, ?, ?, 'completed')", (job["id"], step, index))
    artifacts.collect_node(server.config["SC_STORE"], server.config["SC_STORAGE"],
                           server.config["SC_CONFIG"], job, root, step, index)


def ran(server, user_id, nodes=(("stepone", "0"),), resources=(), passing=False,
        copied_from=None):
    '''An earlier job that ran ``nodes``. With ``passing``, its `steptwo`
    passed `stepone`'s output through as a link, and `stepone` left no log;
    with ``copied_from`` as well, it took `stepone` from that job, so holds no
    archive of it.'''
    job, root = earlier(server, user_id, resources)
    if passing:
        nodes = (("stepone", "0"), ("steptwo", "0"))
    for step, index in nodes:
        node = root / "gcd" / "earlier" / step / index
        (node / "outputs").mkdir(parents=True)
        (node / "outputs" / "gcd.pkg.json").write_text(json.dumps({"from": job["id"]}))
        if not (passing and step == "stepone"):
            (node / f"sc_{step}_{index}.log").write_text("ran\n")
        if passing and step == "steptwo":
            (node / "outputs" / "gcd.vg").symlink_to("../../../stepone/0/outputs/gcd.vg")
        else:
            (node / "outputs" / "gcd.vg").write_text(f"module gcd; endmodule // from {step}\n")
    if copied_from:
        server.config["SC_STORE"].execute(
            'INSERT INTO job_continuations (job_id, step, "index", from_job_id) '
            "VALUES (?, 'stepone', '0', ?)", (job["id"], copied_from))
    for step, index in nodes:
        if not (copied_from and step == "stepone"):
            collect(server, job, root, step, index)
    return job["id"]


def entry(job_id, step="stepone"):
    return {"step": step, "index": "0", "job_id": job_id}


def from_steptwo(project):
    project.option.add_from("steptwo")
    return project


def refused(response):
    assert response.status_code == 422, response.get_json()
    assert slug(response) == "prior-results-unavailable"
    return response.get_json()["reason"]


def submitted(server_client, key, token, archive, **body):
    path, digest, size = archive
    job = stage(server_client, key, token, path, size, **body)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


###########################
# Create
###########################

def test_an_entry_is_recorded_and_echoed(server, server_client, key, token, me):
    earlier_id = ran(server, me)

    response = create(server_client, key, token, continues_from=[entry(earlier_id)])

    assert response.status_code == 201, response.get_json()
    assert response.get_json()["continues_from"] == [entry(earlier_id)]
    rows = server.config["SC_STORE"].all("SELECT * FROM job_continuations WHERE job_id = ?",
                                         (response.get_json()["id"],))
    assert [(row["step"], row["from_job_id"]) for row in rows] == [("stepone", earlier_id)]
    # And absent where the run continues from nothing.
    assert "continues_from" not in create(server_client, key, token,
                                          jobname="job1").get_json()


@pytest.mark.parametrize("value", [
    {"step": "stepone"},                                   # not a list
    [{"step": "stepone", "index": "0"}],                   # a member missing
    [{"step": "stepone", "index": "0", "job_id": "not-a-job-id"}],
    [dict(entry(NO_JOB), extra=1)],
    [{"step": "stepone", "index": "0", "job": NO_JOB}],    # the old spelling
    [entry(NO_JOB), entry(NO_JOB)],                        # one node twice
])
def test_a_malformed_list_is_invalid(server_client, key, token, value):
    response = create(server_client, key, token, continues_from=value)

    assert (response.status_code, slug(response)) == (400, "invalid-request")


def test_anothers_job_and_no_job_are_the_same_answer(server, server_client, key, token):
    '''It confirms nothing.'''
    other_key, other_token = stranger(server_client)
    theirs = ran(server, call(server_client, other_key, "GET", "/v1/me",
                              other_token).get_json()["id"])

    first = create(server_client, key, token, continues_from=[entry(theirs)])
    second = create(server_client, key, token, continues_from=[entry(NO_JOB)])

    assert refused(first) == refused(second) == "not_found"
    assert first.get_json()["detail"].replace(theirs, "") == \
        second.get_json()["detail"].replace(NO_JOB, "")


def test_an_archived_job_may_be_continued_from(server, server_client, key, token, me):
    '''An explicit `-from` may name one: `archived` is registered, never raised.'''
    earlier_id = ran(server, me)
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET archived_at = '2026-09-01T00:00:00.000Z', archived_by = ? "
        "WHERE id = ?", (me, earlier_id))

    response = create(server_client, key, token, continues_from=[entry(earlier_id)])

    assert response.status_code == 201, response.get_json()


def test_a_node_the_job_did_not_run_is_not_completed(server, server_client, key, token, me):
    assert refused(create(server_client, key, token, continues_from=[
        entry(ran(server, me), step="steptwo")])) == "not_completed"


@pytest.mark.parametrize("column,value", [
    ("deleted_at = '2026-09-01T00:00:00.000Z', deleted_reason = 'retention lapsed'", "expired"),
    ("withheld_at = '2026-09-01T00:00:00.000Z', withheld_by = ?", "withheld"),
])
def test_results_gone_or_withheld_cannot_be_used(server, server_client, key, token, me,
                                                 column, value):
    earlier_id = ran(server, me)
    params = (me, earlier_id) if "?" in column else (earlier_id,)
    server.config["SC_STORE"].execute(
        f"UPDATE artifacts SET {column} WHERE job_id = ? AND kind = 'node'", params)

    assert refused(create(server_client, key, token,
                          continues_from=[entry(earlier_id)])) == value


def test_results_built_on_what_nobody_may_use_are_refused(server, server_client, key,
                                                          token, me):
    '''The job's resource set includes what it copies, or it could continue
    from results built on a PDK the caller may not use.'''
    earlier_id = ran(server, me, resources=[("pdk", "secret130")])
    server.config["SC_CONFIG"]._values["denied_resources"] = {"pdk": ["secret*"]}

    response = create(server_client, key, token, continues_from=[entry(earlier_id)])

    assert (response.status_code, slug(response)) == (403, "entitlement-denied")
    assert response.get_json()["resource"] == "secret130"


###########################
# Submit, and the copy
###########################

def test_the_results_are_copied_in_while_staging(server, server_client, key, token, me,
                                                 job_archive, nop_project, dispatcher):
    earlier_id = ran(server, me)

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier_id)])

    assert response.status_code == 202, response.get_json()
    assert response.get_json()["state"] == "staging"      # a copy always stages
    assert wait_for(lambda: dispatcher.submitted)

    outputs = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0" / \
        "stepone" / "0" / "outputs"
    assert (outputs / "gcd.vg").read_text() == "module gcd; endmodule // from stepone\n"
    assert json.loads((outputs / "gcd.pkg.json").read_text()) == {"from": earlier_id}
    # The copied node is no node of this job's.
    assert [row["step"] for row in server.config["SC_STORE"].all(
        "SELECT step FROM job_nodes WHERE job_id = ?", (job["id"],))] == ["steptwo"]


@pytest.mark.parametrize("how", ["uploaded", "skipped"])
def test_a_node_needing_no_copy_queues_without_staging_one(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher, how):
    '''In the upload too: the upload's, so a file changed by hand is used. One
    the earlier job skipped has no results and is not `not_completed`: the run
    reads what fed it, here nothing.'''
    from siliconcompiler.utils.paths import workdir

    earlier_id = ran(server, me)
    if how == "uploaded":
        outputs = os.path.join(workdir(nop_project, step="stepone", index="0"), "outputs")
        os.makedirs(outputs)
        with open(os.path.join(outputs, "gcd.vg"), "w") as f:
            f.write("module gcd; endmodule // mine\n")
    else:
        server.config["SC_STORE"].execute(
            "UPDATE job_nodes SET state = 'skipped' WHERE job_id = ?", (earlier_id,))

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier_id)])

    assert response.status_code == 202, response.get_json()
    assert read(server_client, key, token, job["id"])["state"] == "queued"


def test_a_node_in_neither_is_a_missing_member(server_client, key, token, job_archive,
                                               nop_project, dispatcher):
    _, response = submitted(server_client, key, token, job_archive(from_steptwo(nop_project)))

    assert response.status_code == 422
    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "missing_member")
    assert "stepone/0" in response.get_json()["detail"]
    assert not dispatcher.submitted


def test_a_node_only_copied_in_cannot_be_named_again(server, server_client, key, token, me,
                                                     job_archive, nop_project, dispatcher):
    '''B continues from A, and C names B for a node B only copied, never ran.'''
    b, _ = submitted(server_client, key, token, job_archive(from_steptwo(nop_project)),
                     continues_from=[entry(ran(server, me))])
    assert wait_for(lambda: dispatcher.submitted)

    assert refused(create(server_client, key, token, jobname="job1",
                          continues_from=[entry(b["id"])])) == "not_completed"


@pytest.mark.parametrize("error,detail", [
    (FileNotFoundError, None),
    (OSError(5, "Input/output error"), "this server's store did not answer the copy"),
    (RuntimeError("a bug"), "this server could not get the job ready: RuntimeError")])
def test_results_the_store_cannot_produce_end_the_job(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher,
        monkeypatch, error, detail):
    '''Gone before the copy: found while staging, so `expired` on the job. A
    store that does not answer, or anything unforeseen, is the server's own
    failure: `staging-failed`, saying which.'''
    from siliconcompiler.remote.server.jobs import continuations as jobs

    def broken(archive, *args, **kwargs):
        raise error
    monkeypatch.setattr(jobs, "_extract_outputs", broken)

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(ran(server, me))])

    body = read(server_client, key, token, job["id"])
    if detail is None:
        assert body["state"] == "rejected" and refused(response) == "expired"
    else:
        assert body["state"] == "failed"
        assert body["error"]["type"].endswith("/staging-failed")
        assert detail in body["error"]["detail"]
    assert not dispatcher.submitted


def test_results_withheld_before_the_copy_reject_the_job(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher,
        monkeypatch):
    '''The copy re-checks: an administrator withholding the results after
    submit stops them being used.'''
    from siliconcompiler.remote.server.jobs import JobService

    earlier_id = ran(server, me)
    real = JobService._account_upstream

    def withheld_meanwhile(self, *args, **kwargs):
        found = real(self, *args, **kwargs)
        self._store.execute("UPDATE artifacts SET withheld_at = '2026-09-28T00:00:00.000Z', "
                            "withheld_by = ? WHERE job_id = ? AND kind = 'node'",
                            (me, earlier_id))
        return found
    monkeypatch.setattr(JobService, "_account_upstream", withheld_meanwhile)

    job, response = submitted(server_client, key, token,
                              job_archive(from_steptwo(nop_project)),
                              continues_from=[entry(earlier_id)])

    assert refused(response) == "withheld"
    assert response.get_json()["job_id"] == earlier_id
    assert read(server_client, key, token, job["id"])["state"] == "rejected"
    assert not dispatcher.submitted


def test_a_submit_rechecks_what_create_accepted(server, server_client, key, token, me,
                                                job_archive, nop_project, dispatcher):
    '''Its artifacts can be deleted between the two.'''
    earlier_id = ran(server, me)
    archive, digest, size = job_archive(from_steptwo(nop_project))
    job = stage(server_client, key, token, archive, size, continues_from=[entry(earlier_id)])
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET deleted_at = '2026-09-01T00:00:00.000Z', deleted_by = ? "
        "WHERE id = ?", (me, earlier_id))

    assert refused(outcome(server_client, key, token,
                           submit(server_client, key, token, job["id"], digest, size))) \
        == "deleted"


###########################
# A copied node's links (surface *Passed-through files are resolved while staging*)
###########################

def three_nodes(project, both=False):
    '''stepone -> steptwo -> stepthree, run from stepthree: it reads steptwo,
    and -- with ``both`` -- stepone too.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask

    flow = Flowgraph("passflow")
    for step in ("stepone", "steptwo", "stepthree"):
        flow.node(step, NOPTask())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    if both:
        flow.edge("stepone", "stepthree")
    project.set_flow(flow)
    project.option.add_from("stepthree")
    return project


def copied(server, me, job, step="steptwo"):
    return server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0" / step / "0" / \
        "outputs" / "gcd.vg"


@pytest.mark.parametrize("both", [False, True])
def test_a_copied_nodes_link_gets_its_homes_file_or_stays_a_link(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher, both):
    '''A home not in place is neither copied nor uploaded: its file comes from
    the home node's archive in the earlier job, at the link's path, no bytes
    passing to or from the user. A home also copied keeps the link.'''
    earlier_id = ran(server, me, passing=True)
    continues = [entry(earlier_id, step="steptwo")]
    if both:
        continues.append(entry(earlier_id, step="stepone"))

    job, response = submitted(server_client, key, token,
                              job_archive(three_nodes(nop_project, both=both)),
                              continues_from=continues)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)
    placed = copied(server, me, job)
    assert placed.is_symlink() is both
    assert placed.read_text() == "module gcd; endmodule // from stepone\n"


def test_a_withheld_home_is_refused_naming_it(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher):
    earlier_id = ran(server, me, passing=True)
    server.config["SC_STORE"].execute(
        "UPDATE artifacts SET withheld_at = '2026-09-01T00:00:00.000Z', withheld_by = ? "
        "WHERE job_id = ? AND kind = 'node' AND step = 'stepone'", (me, earlier_id))

    _, response = submitted(server_client, key, token, job_archive(three_nodes(nop_project)),
                            continues_from=[entry(earlier_id, step="steptwo")])

    body = response.get_json()
    assert (response.status_code, slug(response)) == (422, "prior-results-unavailable")
    assert (body["reason"], body["step"], body["index"], body["job_id"]) == \
        ("withheld", "stepone", "0", earlier_id)
    assert not dispatcher.submitted


def test_a_home_the_earlier_job_took_from_a_third_resolves_through_it(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher):
    '''The earlier job copied `stepone` in and has no archive of it: its own
    continuations lead to the job that ran it.'''
    earlier_id = ran(server, me, passing=True, copied_from=ran(server, me, passing=True))
    assert not server.config["SC_STORE"].all(
        "SELECT id FROM artifacts WHERE job_id = ? AND step = 'stepone'", (earlier_id,))

    job, response = submitted(server_client, key, token, job_archive(three_nodes(nop_project)),
                              continues_from=[entry(earlier_id, step="steptwo")])

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)
    assert copied(server, me, job).read_text() == "module gcd; endmodule // from stepone\n"


@pytest.mark.parametrize("target,taken", [("../../../stepone/0/outputs/gcd.vg", True),
                                          ("../../../gcd.pkg.json", False)])
def test_an_uploaded_link_in_upstream_outputs_is_taken_only_into_another(
        server, server_client, key, token, me, job_archive, nop_project, dispatcher,
        target, taken):
    '''A link in an upstream node's `outputs/` into another's, in the same
    archive, is what the client packs for a passed-through file; anywhere
    else, it is refused.'''
    from siliconcompiler.utils.paths import workdir

    three_nodes(nop_project, both=True)
    for step in ("stepone", "steptwo"):
        outputs = os.path.join(workdir(nop_project, step=step, index="0"), "outputs")
        os.makedirs(outputs, exist_ok=True)
        with open(os.path.join(outputs, "gcd.pkg.json"), "w") as f:
            f.write("{}")
        if step == "stepone":
            with open(os.path.join(outputs, "gcd.vg"), "w") as f:
                f.write("module gcd; endmodule\n")
        else:
            os.symlink(target, os.path.join(outputs, "gcd.vg"))

    job, response = submitted(server_client, key, token, job_archive(nop_project))

    if taken:
        assert response.status_code == 202, response.get_json()
        assert wait_for(lambda: dispatcher.submitted)
        assert copied(server, me, job).is_symlink()
    else:
        assert (response.status_code, slug(response)) == (422, "archive-rejected")
        assert response.get_json()["reason"] == "unrequested_member"
        assert "steptwo/0/outputs/gcd.vg is a link" in response.get_json()["detail"]
