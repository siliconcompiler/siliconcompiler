import pytest

from conftest import call, login


pytest.importorskip("flask", reason="the server extra is not installed")


# The portal exists under one rule: every authorization decision goes through
# the code the API handlers call. A portal query that forgets `WHERE user_id =`
# answers 200 and looks correct, and this project has shipped that defect once.
# Most of what is asserted here is that the rule holds.


@pytest.fixture
def dispatcher(server):
    """Shared with the API's own tests, which is the point: the portal runs
    against the same server and the same fake cluster."""
    from test_server_jobs import FakeDispatcher

    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def me(server_client, key, token):
    return call(server_client, key, "GET", "/v1/me", token).get_json()["id"]


@pytest.fixture
def signed_in(server, server_client, key, token):
    '''A browser that has been handed a session by the CLI.'''
    response = call(server_client, key, "POST", "/portal/session", token)
    assert response.status_code == 200

    url = response.get_json()["url"]
    entered = server_client.get(url.split("http://localhost", 1)[1])
    assert entered.status_code == 302
    return server_client


def csrf(client, path="/portal/"):
    page = client.get(path).get_data(as_text=True)
    marker = 'name="csrf" value="'
    return page.split(marker, 1)[1].split('"', 1)[0]


###########################
# Getting in
###########################

def test_a_browser_with_no_session_is_told_how_to_get_one(server_client):
    '''There is no identity provider here and a browser arriving cold holds
    none of what the CLI holds, so the answer is a command rather than a login
    form.'''
    response = server_client.get("/portal/")

    assert response.status_code == 401
    assert "sc-remote -portal" in response.get_data(as_text=True)


def test_the_handover_is_spent_on_arrival(server, server_client, key, token):
    '''🔴 The URL reaches the browser's history and possibly an access log.
    Spending it on arrival is what makes both worthless.'''
    url = call(server_client, key, "POST", "/portal/session",
               token).get_json()["url"]
    path = url.split("http://localhost", 1)[1]

    assert server_client.get(path).status_code == 302
    assert server_client.get(path).status_code == 403


def test_a_handover_link_that_was_never_minted(server_client):
    assert server_client.get("/portal/enter?token=invented").status_code == 403


def test_the_handover_needs_the_machine_key(server_client):
    '''It is the CLI proving possession of its registered key, so an
    unauthenticated caller gets nothing to open.'''
    assert server_client.post("/portal/session").status_code == 401


def test_a_portal_session_is_not_an_api_credential(signed_in):
    '''🔴 It mints no access token and carries no DPoP binding. A path from a
    cookie to an API credential would be the shortest way around the key
    pinning, so there is none.'''
    # The cookie is in the jar; the API still refuses.
    assert signed_in.get("/v1/jobs").status_code == 401
    assert signed_in.get("/v1/me").status_code == 401


def test_signing_out_ends_it(signed_in):
    signed_in.post("/portal/logout", data={"csrf": csrf(signed_in)})

    assert signed_in.get("/portal/").status_code == 401


###########################
# The screens
###########################

@pytest.mark.parametrize("path", ["/portal/", "/portal/devices",
                                  "/portal/account", "/portal/images"])
def test_every_screen_renders(signed_in, path):
    response = signed_in.get(path)

    assert response.status_code == 200
    assert "sc-server" in response.get_data(as_text=True)


def test_a_job_appears_on_the_jobs_screen(server_client, key, token,
                                          job_archive, dispatcher, signed_in):
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    page = signed_in.get("/portal/").get_data(as_text=True)

    assert "gcd" in page
    assert job["id"][:8] in page


def test_the_account_screen_says_the_identity_is_not_verified(signed_in):
    '''The honesty half, in the place a person reads rather than only in a
    startup log.'''
    page = signed_in.get("/portal/account").get_data(as_text=True)

    assert "does not verify who you are" in page
    assert "self-asserted" in page


def test_the_images_screen_says_what_registering_one_means(signed_in):
    '''🔴 The most dangerous write this server has, and the screen says so.'''
    page = signed_in.get("/portal/images").get_data(as_text=True)

    assert "chooses what code executes on the cluster" in page
    assert "declared and unverified" in page


###########################
# The rule the portal exists under
###########################

def test_a_stranger_cannot_read_another_persons_job(
        server, server_client, key, token, job_archive, dispatcher, signed_in):
    '''🔴 Through JobService.owned, which is the same predicate the API
    evaluates -- not a second query that could forget the WHERE.'''
    from siliconcompiler.remote import dpop
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    # A second person, with a portal session of their own.
    other_key = dpop.generate_key()
    other = login(server_client, other_key, subject="machine:2000").get_json()
    url = call(server_client, other_key, "POST", "/portal/session",
               other["access_token"]).get_json()["url"]
    server_client.get(url.split("http://localhost", 1)[1])

    assert server_client.get(f"/portal/jobs/{job['id']}").status_code == 404
    assert server_client.get(
        f"/portal/jobs/{job['id']}/artifacts").status_code == 404


def test_cancelling_from_the_browser_moves_the_job(
        server, server_client, key, token, job_archive, dispatcher, me,
        signed_in):
    '''The gate: a cancel in the browser is the cancel the CLI is waiting on.'''
    from test_server_jobs import running

    job = running(server, server_client, key, token, job_archive, me)

    signed_in.post(f"/portal/jobs/{job['id']}/cancel",
                   data={"csrf": csrf(signed_in), "reason": "from the portal"})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}",
                token).get_json()
    assert read["state"] == "cancelling"
    assert dispatcher.cancelled == ["fake:1"]


def test_a_form_from_somewhere_else_is_refused(signed_in, server, server_client,
                                               key, token, job_archive,
                                               dispatcher, me):
    '''SameSite=Strict already refuses the cookie on a cross-site POST. This is
    the half that does not depend on the browser being recent.'''
    from test_server_jobs import running

    job = running(server, server_client, key, token, job_archive, me)

    response = signed_in.post(f"/portal/jobs/{job['id']}/cancel",
                              data={"csrf": "not-the-one"})

    assert response.status_code == 403
    assert not dispatcher.cancelled


###########################
# What a run produced
###########################

@pytest.fixture
def finished(server, server_client, key, token, job_archive, dispatcher, me):
    '''A job that ran to completion, with its results indexed.'''
    from test_server_jobs import stage, submit
    from siliconcompiler.remote.server import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    for step in ("stepone", "steptwo"):
        node = root / step / "0"
        node.mkdir(parents=True, exist_ok=True)
        (node / f"sc_{step}_0.log").write_text(f"siliconcompiler says {step}\n")
        (node / f"{step}.log").write_text(f"the tool says {step}\n")

    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "completed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:00:05.000Z",
        "nodes": {"stepone/0": {"state": "completed"},
                  "steptwo/0": {"state": "completed"}}})

    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    return job


def test_the_artifacts_screen_lists_them(signed_in, finished):
    '''🔴 The listing returns (items, cursor). Handing the tuple straight to a
    template renders a page with nothing on it and no error, which is how this
    shipped once.'''
    page = signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts").get_data(as_text=True)

    assert "download" in page
    assert "logs" in page


def test_a_node_offers_every_log_it_wrote(signed_in, finished):
    '''🔴 SiliconCompiler's own record of the node and what the TOOL printed
    answer different questions, and a synthesis error is only in the second.'''
    page = signed_in.get(
        f"/portal/jobs/{finished['id']}/logs/stepone/0").get_data(as_text=True)

    assert "sc_stepone_0.log" in page
    assert "stepone.log" in page
    # SiliconCompiler's own first: it says what the node was asked to do.
    assert "siliconcompiler says stepone" in page

    other = signed_in.get(
        f"/portal/jobs/{finished['id']}/logs/stepone/0?file=stepone.log"
    ).get_data(as_text=True)
    assert "the tool says stepone" in other


def test_the_job_page_draws_the_flow(signed_in, finished):
    '''Drawn on the server. The alternative is a JavaScript graph library, and
    a node toolchain in the release pipeline is paid by every SC release.'''
    page = signed_in.get(f"/portal/jobs/{finished['id']}").get_data(as_text=True)

    assert "<svg" in page
    assert 'class="wire"' in page
    assert page.count('class="node ') == 2


def test_artifacts_appear_beside_the_node_that_made_them(signed_in, finished):
    page = signed_in.get(f"/portal/jobs/{finished['id']}").get_data(as_text=True)

    assert "/artifacts/" in page


###########################
# Curating the registry
###########################

def test_software_can_be_retired_from_the_screen(signed_in, server):
    '''🔴 Retiring a VERSION says *not this one*; retiring the SOFTWARE says
    *not any more*, and the tool stops raising a requirement at all. Both are
    reachable, because an operator who can only add cannot correct a
    mistake.'''
    from siliconcompiler.remote.server import images

    store = server.config["SC_STORE"]
    actor = store.upsert_user("operator", "someone@host")["id"]
    images.register_software(store, "yosys", "Yosys", actor)
    images.register_version(store, "yosys", "0.44", actor)

    token = csrf(signed_in, "/portal/images")

    signed_in.post("/portal/images/software/yosys/retire",
                   data={"csrf": token, "version": "0.44"})
    assert store.one("SELECT retired_at FROM software_versions "
                     "WHERE software_name = 'yosys'")["retired_at"]
    assert not store.one("SELECT retired_at FROM software "
                         "WHERE name = 'yosys'")["retired_at"]

    signed_in.post("/portal/images/software/yosys/retire", data={"csrf": token})
    assert store.one("SELECT retired_at FROM software "
                     "WHERE name = 'yosys'")["retired_at"]


def test_a_retired_distribution_offers_no_per_version_button(signed_in, server):
    '''Once the whole name has stopped raising a requirement, retiring one of
    its versions would change nothing -- and offering it says otherwise.'''
    from siliconcompiler.remote.server import images

    store = server.config["SC_STORE"]
    actor = store.upsert_user("operator", "someone@host")["id"]
    images.register_software(store, "klayout", "KLayout", actor)
    images.register_version(store, "klayout", "0.29", actor)

    live = signed_in.get("/portal/images").get_data(as_text=True)
    assert live.count("retire</button>") == 1

    images.retire_software(store, "klayout", actor)

    retired = signed_in.get("/portal/images").get_data(as_text=True)
    assert "retire</button>" not in retired
    assert "Stop curating" not in retired


###########################
# A failed job says why, on the page
###########################

@pytest.fixture
def died(server, server_client, key, token, job_archive, dispatcher, me):
    '''A run that failed before it reached a node -- the shape that prompted
    the question: state `failed`, every node `cancelled`, nothing else said.'''
    from test_server_jobs import stage, submit
    from siliconcompiler.remote.server import runspec
    from siliconcompiler.remote.server.dispatch import RUN_LOG

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    jobroot = server.config["SC_JOBS"].job_root(me, job["id"])
    (jobroot / RUN_LOG).write_text(
        "Traceback (most recent call last):\n"
        "RuntimeError: git is required to import GitPython\n")

    runspec.write_progress(jobroot / "gcd" / "job0" / runspec.PROGRESS_FILENAME, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:00:02.000Z",
        "error": "RuntimeError: git is required to import GitPython",
        "nodes": {"stepone/0": {"state": "cancelled"},
                  "steptwo/0": {"state": "cancelled"}}})

    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    return job


def test_the_page_says_why_it_failed(signed_in, died):
    '''The title is frozen and reads the same on every failure there has ever
    been. The detail is the only part of the banner that is about this run.'''
    page = signed_in.get(f"/portal/jobs/{died['id']}").get_data(as_text=True)

    assert "The run failed" in page
    assert "git is required to import GitPython" in page


def test_the_page_says_no_node_failed_when_none_did(signed_in, died):
    '''🔴 The question that prompted this: a failed job whose nodes all read
    `cancelled`, with nothing on the page to say that is what an unreached node
    looks like.'''
    page = signed_in.get(f"/portal/jobs/{died['id']}").get_data(as_text=True)

    assert "No node failed" in page
    assert "the job ended before that node started" in page


def test_the_run_log_is_on_the_page_of_the_job_that_left_no_other(signed_in, died):
    '''Before this the listing was empty and the only account of what happened
    stayed on the server, where the person who ran the job could not reach
    it.'''
    page = signed_in.get(f"/portal/jobs/{died['id']}").get_data(as_text=True)

    assert "The job itself" in page
    assert "download" in page


def test_a_cancelled_job_is_not_told_nobody_cancelled_it(
        signed_in, server, server_client, key, token, job_archive, dispatcher, me):
    '''The note explains `cancelled` on a node of a job that ended some other
    way. On a job somebody DID cancel the word means what it looks like, and
    the note would contradict the page.'''
    from test_server_jobs import stage, submit
    from siliconcompiler.remote.server import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-23T10:00:00.000Z",
        "nodes": {"stepone/0": {"state": "running"},
                  "steptwo/0": {"state": "pending"}}})

    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)
    dispatcher.alive = False
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    page = signed_in.get(f"/portal/jobs/{job['id']}").get_data(as_text=True)
    assert "cancelled" in page
    assert "not\nthat anyone cancelled it" not in page
    assert "the job ended before that node started" not in page


###########################
# Looking inside an archive
###########################

def test_a_bundle_can_be_browsed_without_downloading_it(signed_in, finished,
                                                        server, me):
    '''🔴 What "report viewing" needs: a node's reports are inside its bundle,
    and a page that can only hand over the whole archive cannot show one.'''
    store = server.config["SC_STORE"]
    row = store.one(
        'SELECT id FROM artifacts WHERE job_id = ? AND kind = ? AND step = ?',
        (finished["id"], "bundle", "stepone"))

    page = signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts/{row['id']}/inside"
    ).get_data(as_text=True)

    assert "sc_stepone_0.log" in page


def test_one_file_out_of_an_archive_renders_as_text(signed_in, finished, server):
    store = server.config["SC_STORE"]
    row = store.one(
        'SELECT id FROM artifacts WHERE job_id = ? AND kind = ? AND step = ?',
        (finished["id"], "bundle", "stepone"))

    page = signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts/{row['id']}/inside"
        "?file=sc_stepone_0.log").get_data(as_text=True)

    assert "siliconcompiler says stepone" in page


def test_a_name_the_archive_does_not_hold_is_not_found(signed_in, finished,
                                                       server):
    '''🔴 Matched against the archive's own list, never joined into a path. The
    name comes from a query string and a tar can hold `../` whatever this
    server does.'''
    store = server.config["SC_STORE"]
    row = store.one(
        'SELECT id FROM artifacts WHERE job_id = ? AND kind = ? AND step = ?',
        (finished["id"], "bundle", "stepone"))

    response = signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts/{row['id']}/inside"
        "?file=../../../etc/passwd")

    assert response.status_code == 404


def test_the_raw_route_never_serves_html(signed_in, finished, server, me):
    '''🔴 An artifact is bytes a JOB produced. Served as text/html from this
    origin, a design that writes one would be running its own script on the
    portal.'''
    store = server.config["SC_STORE"]
    root = server.config["SC_JOBS"].job_root(me, finished["id"]) / "gcd" / "job0"
    (root / "stepone" / "0" / "trouble.html").write_text(
        "<script>alert(1)</script>")

    # Re-index so the new file is in the bundle.
    store.execute("DELETE FROM artifacts WHERE job_id = ? AND kind = 'bundle'",
                  (finished["id"],))
    from siliconcompiler.remote.server import artifacts as indexer
    job = store.one("SELECT * FROM jobs WHERE id = ?", (finished["id"],))
    indexer.collect_node(store, server.config["SC_STORAGE"],
                         server.config["SC_CONFIG"], job,
                         server.config["SC_JOBS"].job_root(me, finished["id"]),
                         "stepone", "0")

    row = store.one(
        'SELECT id FROM artifacts WHERE job_id = ? AND kind = ? AND step = ?',
        (finished["id"], "bundle", "stepone"))
    response = signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts/{row['id']}/inside"
        "?file=trouble.html&raw=1")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


###########################
# Deleting what a run produced
###########################

def test_delete_needs_the_job_named(signed_in, finished):
    '''⚠️ A speed bump, not a security control -- CSRF is what stops somebody
    else pressing it. It is here because the button used to sit one position
    from the link people click constantly, and the two do opposite things.'''
    token = csrf(signed_in, f"/portal/jobs/{finished['id']}/artifacts")

    refused = signed_in.post(f"/portal/jobs/{finished['id']}/delete",
                             data={"csrf": token, "confirm": "something else"})
    assert refused.status_code == 400

    accepted = signed_in.post(f"/portal/jobs/{finished['id']}/delete",
                              data={"csrf": token, "confirm": "gcd/job0"})
    assert accepted.status_code == 302


def test_the_delete_button_is_on_the_artifacts_page_and_not_the_job_page(
        signed_in, finished):
    job = signed_in.get(f"/portal/jobs/{finished['id']}").get_data(as_text=True)
    page = signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts").get_data(as_text=True)

    assert "/delete" not in job
    assert "/delete" in page


def test_the_job_page_offers_the_runs_own_log(signed_in, died):
    '''The first thing anybody wants on a job that failed outside a node, and
    it was three clicks away at the bottom of a table.'''
    page = signed_in.get(f"/portal/jobs/{died['id']}").get_data(as_text=True)
    assert ">Job log</a>" in page


def test_the_job_page_opens_an_archive_rather_than_downloading_it(
        signed_in, finished, server):
    '''🔴 Clicking `reports` on the job page SHOWS you the reports. It used to
    download a .tar.gz, with the only way to look inside sitting on the
    artifacts page -- the page nobody reaches first.'''
    store = server.config["SC_STORE"]
    bundle = store.one(
        "SELECT id FROM artifacts WHERE job_id = ? AND kind = 'bundle' "
        "AND step = 'stepone'", (finished["id"],))

    page = signed_in.get(f"/portal/jobs/{finished['id']}").get_data(as_text=True)

    assert f"/artifacts/{bundle['id']}/inside" in page


def test_the_browse_page_offers_the_whole_archive(signed_in, finished, server):
    '''🔴 Making the job page browse an archive took away the only download
    there was. Picking files out of a page one at a time is not a substitute
    for taking the lot.'''
    row = server.config["SC_STORE"].one(
        "SELECT id FROM artifacts WHERE job_id = ? AND kind = 'bundle' "
        "AND step = 'stepone'", (finished["id"],))

    page = signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts/{row['id']}/inside"
    ).get_data(as_text=True)

    assert "Download all of it" in page
    assert f"/artifacts/{row['id']}\"" in page or f"/artifacts/{row['id']}'" in page


def test_the_account_page_shows_the_ceiling_and_the_default(signed_in, server,
                                                            server_client, key,
                                                            token):
    '''🔴 Two columns, because one cannot say whether anybody set it. "1.0 KiB"
    alone answers neither *is this mine* nor *what would it be otherwise*.'''
    from siliconcompiler.remote.server import accounts

    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    accounts.set_limit(server.config["SC_STORE"], me, "auto_fetch_max_bytes",
                       1024, me, note="a slow link")

    page = signed_in.get("/portal/account").get_data(as_text=True)

    assert "auto_fetch_max_bytes" in page
    assert "1.0 KiB" in page                       # what this account gets
    assert "100 MiB" in page                       # what the deployment gives
    assert "set for you" in page
    # Read-only: a ceiling is the operator's policy and this deployment has no
    # admin mode, so the screen shows it and never posts it.
    assert "portal.set_limit" not in page


def test_the_nodes_table_is_in_the_order_the_run_reaches_them(signed_in, finished):
    '''⚠️ The API lists nodes by name, which puts `elaborate` in the middle of a
    23-node asicflow between `cts` and `floorplan`. Fine for a listing a client
    sorts itself, wrong for a table somebody reads top to bottom.'''
    from siliconcompiler.remote.server.portal import running_order

    job = {"nodes": [
        {"step": "zzz_last", "index": "0"},
        {"step": "aaa_middle", "index": "0"},
        {"step": "mmm_first", "index": "0"},
    ]}
    edges = [
        {"from_step": "mmm_first", "from_index": "0",
         "to_step": "aaa_middle", "to_index": "0"},
        {"from_step": "aaa_middle", "from_index": "0",
         "to_step": "zzz_last", "to_index": "0"},
    ]

    assert [n["step"] for n in running_order(job, edges)] == [
        "mmm_first", "aaa_middle", "zzz_last"]


def test_nodes_at_the_same_depth_break_ties_on_the_name(signed_in):
    '''So two runs of the same flow render identically and a reload never
    reshuffles the rows.'''
    from siliconcompiler.remote.server.portal import running_order

    job = {"nodes": [{"step": "b", "index": "1"}, {"step": "b", "index": "0"},
                     {"step": "a", "index": "0"}]}

    assert [(n["step"], n["index"]) for n in running_order(job, [])] == [
        ("a", "0"), ("b", "0"), ("b", "1")]


###########################
# Arriving cold on a job link
###########################

def test_a_cold_link_to_a_job_comes_back_to_that_job(server_client, key, token,
                                                     finished):
    '''🔴 `web_url` is a link somebody clicks cold. Without this the handover
    always landed on the jobs list, so the answer to "here is your job" was
    "here is a list, find it again".'''
    page = f"/portal/jobs/{finished['id']}"

    turned_away = server_client.get(page)
    assert turned_away.status_code == 401
    assert "sc-remote -portal" in turned_away.get_data(as_text=True)

    url = call(server_client, key, "POST", "/portal/session", token).get_json()["url"]
    entered = server_client.get(url.split("http://localhost", 1)[1])

    assert entered.status_code == 302
    assert entered.headers["Location"].endswith(page)


def test_a_cold_link_to_nothing_in_particular_lands_on_the_jobs_list(
        server_client, key, token):
    url = call(server_client, key, "POST", "/portal/session", token).get_json()["url"]
    entered = server_client.get(url.split("http://localhost", 1)[1])

    assert entered.status_code == 302
    assert entered.headers["Location"].rstrip("/").endswith("/portal")


def test_the_return_path_is_never_an_open_redirect(server_client, key, token):
    '''🔴 Anything can set a cookie on this origin, and a redirect that follows
    one is the classic phishing primitive -- made worse here because the person
    has just been told this link is the trustworthy way in.'''
    url = call(server_client, key, "POST", "/portal/session", token).get_json()["url"]

    for hostile in ("//evil.example/", "https://evil.example/",
                    "/etc/passwd", "/v1/jobs"):
        server_client.set_cookie("sc_portal_next", hostile, domain="localhost")
        entered = server_client.get(url.split("http://localhost", 1)[1])
        if entered.status_code == 302:
            assert "evil.example" not in entered.headers["Location"]
            assert entered.headers["Location"].rstrip("/").endswith("/portal")
        # A spent handover is also an acceptable answer here.
        server_client.delete_cookie("sc_portal_next", domain="localhost")


###########################
# Watching a run without pressing anything
###########################

def test_a_running_job_page_refreshes_itself(server_client, key, token,
                                             job_archive, dispatcher, signed_in):
    '''⚠️ `<meta http-equiv="refresh">` rather than a timer: the browser's own
    mechanism, it stops when the tab closes, and it survives scripting being
    off.'''
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    page = signed_in.get(f"/portal/jobs/{job['id']}").get_data(as_text=True)

    assert 'http-equiv="refresh"' in page
    assert "refresh now" in page


def test_a_finished_job_page_does_not(signed_in, finished):
    '''🔴 Only while there is something to watch. A page that reloads for ever
    reloads while somebody reads a finished run, and keeps a request in flight
    against a server nobody is looking at.'''
    page = signed_in.get(f"/portal/jobs/{finished['id']}").get_data(as_text=True)

    assert 'http-equiv="refresh"' not in page
    assert "refresh now" not in page


def test_the_jobs_list_refreshes_only_while_something_is_going(
        server_client, key, token, job_archive, dispatcher, signed_in, finished):
    from test_server_jobs import stage, submit

    quiet = signed_in.get("/portal/").get_data(as_text=True)
    assert 'http-equiv="refresh"' not in quiet

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    busy = signed_in.get("/portal/").get_data(as_text=True)
    assert 'http-equiv="refresh"' in busy
    assert "1 still going" in busy


###########################
# What this deployment is
###########################

def test_the_server_screen_answers_what_v1_answers(signed_in, server_client):
    '''🔴 Built by calling the endpoints' own code. A screen that renders a
    second opinion of `GET /v1` can disagree with the API about what this
    server promises, which is worse than no screen because somebody would
    trust it.'''
    import json as _json

    published = _json.loads(server_client.get("/v1").get_data())
    page = signed_in.get("/portal/server").get_data(as_text=True)

    assert published["api_version"] in page
    assert published["identity_assurance"] in page
    for name in published["software"]:
        assert name in page
    for limit in published["limits"]:
        assert limit in page
    for feature in published["features"]:
        assert feature in page


def test_the_server_screen_shows_liveness(signed_in):
    page = signed_in.get("/portal/server").get_data(as_text=True)

    assert "Health" in page
    assert "pass" in page


def test_the_server_screen_carries_the_raw_block(signed_in, server_client):
    '''⚠️ This deployment is a reference implementation, so "what does GET /v1
    actually return" is a question its own portal should answer without
    curl.'''
    page = signed_in.get("/portal/server").get_data(as_text=True)

    assert "&#34;api_version&#34;" in page or '"api_version"' in page
    assert "<details>" in page


def test_the_server_screen_needs_a_session(server_client):
    assert server_client.get("/portal/server").status_code == 401
