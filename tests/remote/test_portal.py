import datetime
import json
import tarfile

import pytest

from conftest import call, login, outcome, slug


pytest.importorskip("flask", reason="the server extra is not installed")

from test_server_jobs import FakeDispatcher, running, stage, submit  # noqa: E402

from siliconcompiler.remote.server.outputs import artifacts  # noqa: E402
from siliconcompiler.remote.server.running import runspec  # noqa: E402


# The portal's rule: every authorization decision goes through the code the API
# handlers call. A query that forgets `WHERE user_id =` answers 200 and looks
# correct, and this project has shipped that defect once.

COMPLETED = {"state": "completed", "started_at": "2026-09-23T10:00:00.000Z",
             "finished_at": "2026-09-23T10:00:05.000Z",
             "nodes": {"stepone/0": {"state": "completed"},
                       "steptwo/0": {"state": "completed"}}}


def browser(client, key, token, headers=None, **named):
    '''`POST /v1/auth/browser`, endpoint 6: the page for what `named` names.'''
    return call(client, key, "POST", "/v1/auth/browser", token, json=named,
                headers=headers)


def enter(client, response):
    '''Spend the sign-in endpoint 6 answered, as a browser does.'''
    return client.get(response.get_json()["url"].split("http://localhost", 1)[1])


def stranger(client):
    '''A second person: their key and access token.'''
    from siliconcompiler.remote import dpop

    other_key = dpop.generate_key()
    return other_key, login(client, other_key, subject="machine:2000").get_json()["access_token"]


def page(client, path):
    return client.get(path).get_data(as_text=True)


def csrf(client, path="/portal/"):
    return page(client, path).split('name="csrf" value="', 1)[1].split('"', 1)[0]


def submitted(client, key, token, job_archive):
    archive, digest, size = job_archive()
    job = stage(client, key, token, archive, size)
    submit(client, key, token, job["id"], digest, size)
    return job


def write_progress(server, me, job, body):
    runspec.write_json(server.config["SC_JOBS"].job_root(me, job["id"])
                       / runspec.PROGRESS_FILENAME, body)


def node_root(server, me, job, step="stepone"):
    return server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0" / step / "0"


def artifact_id(server, job, kind="node", step="stepone"):
    return server.config["SC_STORE"].one(
        "SELECT id FROM artifacts WHERE job_id = ? AND kind = ? AND step = ?",
        (job["id"], kind, step))["id"]


def collect(server, me, job, step="stepone", fresh=True):
    '''Index a node again, so files written into its tree are in its archive.'''
    store = server.config["SC_STORE"]
    if fresh:
        store.execute("DELETE FROM artifacts WHERE job_id = ? AND kind = 'node'", (job["id"],))
    row = store.one("SELECT * FROM jobs WHERE id = ?", (job["id"],))
    artifacts.collect_node(store, server.config["SC_STORAGE"], server.config["SC_CONFIG"],
                           row, server.config["SC_JOBS"].job_root(me, job["id"]), step, "0")


@pytest.fixture
def dispatcher(server):
    '''The API tests' fake cluster: the portal runs against the same server.'''
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def me(server_client, key, token):
    return call(server_client, key, "GET", "/v1/me", token).get_json()["id"]


@pytest.fixture
def signed_in(server, server_client, key, token):
    '''A browser that has been handed a session by the CLI.'''
    response = browser(server_client, key, token)
    assert response.status_code == 200
    assert enter(server_client, response).status_code == 302
    return server_client


@pytest.fixture
def finished(server, server_client, key, token, job_archive, dispatcher, me):
    '''A job that ran to completion, with its results indexed.'''
    job = submitted(server_client, key, token, job_archive)
    for step in ("stepone", "steptwo"):
        node = node_root(server, me, job, step)
        node.mkdir(parents=True, exist_ok=True)
        (node / f"sc_{step}_0.log").write_text(f"siliconcompiler says {step}\n")
        (node / f"{step}.log").write_text(f"the tool says {step}\n")
    write_progress(server, me, job, COMPLETED)

    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    return job


def test_the_portal_is_served_wherever_the_api_is(signed_in):
    '''Over plain http to a peer beyond this machine too: the server warns
    at startup instead.'''
    remote = {"REMOTE_ADDR": "10.1.2.3"}

    assert signed_in.get("/portal/", environ_base=remote).status_code == 200
    assert signed_in.get("/portal/", base_url="https://localhost",
                         environ_base=remote).status_code == 200


@pytest.mark.parametrize("origins,warned", [
    (["http://lab.example:8080"], True),
    (["http://10.1.2.3:8080", "http://localhost:8080"], True),
    (["http://localhost:8080", "http://127.0.0.1:8080", "http://[::1]:8080"], False),
    (["https://lab.example"], False),
])
def test_plain_http_beyond_this_machine_is_warned_at_startup(tmp_path, caplog, origins,
                                                             warned):
    from siliconcompiler.remote.server.app import create_app

    with caplog.at_level("WARNING", logger="sc-server"):
        create_app(tmp_path / "datadir", public_origins=origins)

    said = [record.message for record in caplog.records if "plain http" in record.message]
    assert bool(said) == warned
    if warned:
        assert "https through a reverse proxy" in said[0]


@pytest.mark.parametrize("base,origins,refused", [
    ("http://sc.example", ["https://sc.example"], True),
    ("http://sc.example", ["http://localhost:8080", "https://sc.example"], True),
    ("http://localhost:8080", ["http://localhost:8080"], False),
    # An `http` answer may send the client to either scheme.
    ("https://sc.example", ["http://localhost:8080"], False),
    ("https://sc.example", ["http://localhost:8080", "https://sc.example"], False),
])
def test_a_sign_in_link_is_never_plain_http_beside_an_https_origin(tmp_path, base,
                                                                   origins, refused):
    '''An `https` answer sends only to `https` URLs, and
    the link is built on `web_url_base` whatever origin the request used.'''
    from siliconcompiler.remote.server.app import create_app

    datadir = tmp_path / "datadir"
    datadir.mkdir()
    (datadir / "config.json").write_text(json.dumps({"web_url_base": base}))

    if refused:
        with pytest.raises(ValueError, match="web_url_base must be https"):
            create_app(datadir, public_origins=origins)
    else:
        create_app(datadir, public_origins=origins)


@pytest.mark.parametrize("path", ["/portal/", "/portal/server"])
def test_a_browser_with_no_session_is_told_how_to_get_one(server_client, path):
    '''No identity provider here, so the answer is a command, not a form.'''
    response = server_client.get(path)

    assert response.status_code == 401
    assert "sc-remote -portal" in response.get_data(as_text=True)


def test_a_handover_works_once_before_it_expires_and_only_if_minted(
        monkeypatch, server_client, key, token):
    '''The URL reaches browser history and access logs; spending it on
    arrival makes both worthless.'''
    from siliconcompiler.remote.server import portal

    response = browser(server_client, key, token)
    assert enter(server_client, response).status_code == 302
    assert enter(server_client, response).status_code == 403

    assert server_client.get("/portal/enter?token=invented").status_code == 403

    monkeypatch.setattr(portal, "HANDOVER_SECONDS", -1)
    assert enter(server_client, browser(server_client, key, token)).status_code == 403


def test_a_sign_in_says_when_it_stops_working_and_is_kept_by_nobody(
        server_client, key, token):
    '''`expires_at` is set: this portal has no sign-in of its own.'''
    response = browser(server_client, key, token)
    body = response.get_json()

    assert set(body) == {"url", "expires_at"}
    assert response.headers["Cache-Control"] == "private, no-store"
    when = datetime.datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    left = (when - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
    assert 0 < left <= 60


def test_the_portal_session_route_is_gone(server_client, key, token):
    '''Retired: every page comes from endpoint 6, under `/v1`.'''
    response = call(server_client, key, "POST", "/portal/session", token, json={})

    assert response.status_code in (404, 405)


def test_the_landing_is_the_jobs_list_or_the_named_job(server_client, key, token,
                                                       finished):
    '''No body at all reads as `{}`. A job's landing is built from its id;
    no path a caller sends is followed.'''
    empty = call(server_client, key, "POST", "/v1/auth/browser", token)
    assert empty.status_code == 200

    for response in (empty, browser(server_client, key, token)):
        entered = enter(server_client, response)
        assert entered.status_code == 302
        assert entered.headers["Location"].rstrip("/").endswith("/portal")

    entered = enter(server_client, browser(server_client, key, token, job_id=finished["id"]))
    assert entered.status_code == 302
    assert entered.headers["Location"].endswith(f"/portal/jobs/{finished['id']}")


def test_a_terms_id_is_a_document_nobody_here_can_see(server_client, key, token):
    '''This profile serves no terms documents, so every one is invisible.'''
    response = browser(server_client, key, token, terms_id="gf22-nda")

    assert (response.status_code, slug(response)) == (404, "not-found")


def test_an_artifact_with_nothing_to_ask_for_is_not_permitted(server_client, key, token,
                                                              finished):
    '''Every artifact reads `can_request_access: false`: there is no page.'''
    items = call(server_client, key, "GET", f"/v1/jobs/{finished['id']}/artifacts",
                 token).get_json()["items"]
    assert items and all(item["can_request_access"] is False for item in items)

    response = browser(server_client, key, token, artifact_id=items[0]["id"])

    assert (response.status_code, slug(response)) == (403, "not-permitted")


@pytest.mark.parametrize("member", ["job_id", "artifact_id"])
def test_an_invisible_job_or_artifact_is_not_found(server_client, key, token, finished,
                                                   member):
    '''Another person's is the same answer as one that does not exist: the job
    read predicate, applied to an artifact through its job.'''
    items = call(server_client, key, "GET", f"/v1/jobs/{finished['id']}/artifacts",
                 token).get_json()["items"]
    named = finished["id"] if member == "job_id" else items[0]["id"]

    other_key, other = stranger(server_client)
    for value in (named, "01J9NOSUCHTHING"):
        response = browser(server_client, other_key, other, **{member: value})
        assert (response.status_code, slug(response)) == (404, "not-found")


@pytest.mark.parametrize("request_body,status,problem", [
    ({"json": {"job_id": "J1", "terms_id": "tos"}}, 400, "invalid-request"),
    # `next` too: a redirect following a caller's input is an open redirect.
    ({"json": {"next": "/portal/jobs/J1"}}, 400, "invalid-request"),
    ({"json": {"job_id": 7}}, 400, "invalid-request"),
    ({"json": ["job_id"]}, 400, "invalid-request"),
    ({"data": "job_id=J1", "content_type": "application/x-www-form-urlencoded"},
     415, "unsupported-media-type"),
])
def test_a_body_naming_anything_but_one_page_is_refused(server_client, key, token,
                                                        request_body, status, problem):
    response = call(server_client, key, "POST", "/v1/auth/browser", token, **request_body)

    assert (response.status_code, slug(response)) == (status, problem)


def test_only_an_interactive_session_gets_a_page(server, server_client, key, token):
    '''A session is CI exactly when a CI key minted it, so a
    client-credentials one is interactive. Nobody is at a browser in CI; this
    profile mints no CI session, so the family is made one here.'''
    me = call(server_client, key, "GET", "/v1/me", token).get_json()
    assert me["session"]["kind"] == "interactive"

    server.config["SC_STORE"].execute(
        "UPDATE token_families SET kind = 'ci', device_id = NULL")

    response = browser(server_client, key, token)
    assert (response.status_code, slug(response)) == (403, "not-permitted")


@pytest.mark.parametrize("base,expected", [
    ("http://sc.example/", "http://sc.example/portal/enter?token="),
    # Without one, the configured origin the DPoP `htu` matched.
    (None, "http://localhost/portal/enter?token="),
])
@pytest.mark.parametrize("headers", [
    {"Host": "evil.example"},
    {"X-Forwarded-Host": "evil.example"},
    {"Host": "evil.example", "X-Forwarded-Host": "evil.example",
     "X-Forwarded-Proto": "https"},
])
def test_the_link_is_never_built_on_a_request_header(server, server_client, key, token,
                                                     base, expected, headers):
    '''Or anyone who can set one mints a link pasted into a ticket.'''
    server.config["SC_CONFIG"]._values["web_url_base"] = base

    url = browser(server_client, key, token, headers=headers).get_json()["url"]

    assert url.startswith(expected)
    assert "evil" not in url


def test_a_portal_session_is_not_an_api_credential(signed_in):
    '''No access token, no DPoP binding: a cookie-to-credential path would
    be the shortest way around key pinning. Nor does the cookie mint a
    handover, which is the CLI proving its key.'''
    assert signed_in.post("/v1/auth/browser", json={}).status_code == 401
    assert signed_in.get("/v1/jobs").status_code == 401
    assert signed_in.get("/v1/me").status_code == 401


def test_signing_out_ends_it(signed_in):
    signed_in.post("/portal/logout", data={"csrf": csrf(signed_in)})

    assert signed_in.get("/portal/").status_code == 401


@pytest.mark.parametrize("path,says", [
    ("/portal/", []),
    ("/portal/devices", []),
    # The honesty half, where a person reads it; and `usage.concurrent_jobs`,
    # since a template naming a member the object lacks renders nothing.
    ("/portal/account", ["does not verify who you are", "self_asserted",
                         "<b>Jobs running now</b><br>0</div>"]),
    # The most dangerous write this server has, and the screen says so.
    ("/portal/images", ["chooses what code executes on the cluster",
                        "declared and unverified"]),
])
def test_every_screen_renders(signed_in, path, says):
    response = signed_in.get(path)
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    for phrase in ["sc-server", *says]:
        assert phrase in text


def test_the_server_screen_answers_what_v1_answers(signed_in, server_client):
    '''Built from the endpoints' own code: a second opinion of `GET /v1`
    could disagree with the API. A reference implementation, so the raw
    block is there too, with liveness.'''
    published = json.loads(server_client.get("/v1").get_data())
    text = page(signed_in, "/portal/server")

    assert published["api_version"] in text
    assert published["identity_assurance"] in text
    for name in [*published["software"], *published["limits"], *published["features"]]:
        assert name in text
    assert "Health" in text and "pass" in text
    assert "&#34;api_version&#34;" in text or '"api_version"' in text
    assert "<details>" in text


def test_a_stranger_cannot_read_another_persons_job(
        server_client, key, token, job_archive, dispatcher, signed_in):
    '''Through JobService.owned, the API's own predicate.'''
    job = submitted(server_client, key, token, job_archive)

    other_key, other = stranger(server_client)
    enter(server_client, browser(server_client, other_key, other))

    assert server_client.get(f"/portal/jobs/{job['id']}").status_code == 404
    assert server_client.get(f"/portal/jobs/{job['id']}/artifacts").status_code == 404


def test_cancelling_from_the_browser_moves_the_job_and_needs_its_own_form(
        server, server_client, key, token, job_archive, dispatcher, me, signed_in):
    '''A browser cancel is the cancel the CLI waits on. A form from elsewhere
    is refused, not relying on SameSite=Strict in a recent browser.'''
    job = running(server, server_client, key, token, job_archive, me)

    forged = signed_in.post(f"/portal/jobs/{job['id']}/cancel", data={"csrf": "not-the-one"})
    assert forged.status_code == 403
    assert not dispatcher.cancelled

    signed_in.post(f"/portal/jobs/{job['id']}/cancel",
                   data={"csrf": csrf(signed_in), "reason": "from the portal"})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "cancelling"
    assert dispatcher.cancelled == ["fake:1"]


def test_a_nodes_metrics_come_from_the_table_the_jobs_end_filled(
        server, server_client, key, token, job_archive, dispatcher, me, signed_in):
    '''The final manifest is read once, as plain JSON, when the job ends;
    the panel reads the table, never the manifest.'''
    job = submitted(server_client, key, token, job_archive)
    manifest = node_root(server, me, job).parents[1] / "gcd.pkg.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "metric": {"cellarea": {"node": {"stepone": {"0": {"value": 12.5}}}}},
        "record": {"status": {"node": {"stepone": {"0": {"value": "success"}}}}}}))
    write_progress(server, me, job, COMPLETED)
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    manifest.unlink()

    response = signed_in.get(f"/portal/jobs/{job['id']}/metrics/stepone/0")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "cellarea" in text and "12.5" in text and "success" in text
    assert "/metrics/stepone/0" in page(signed_in, f"/portal/jobs/{job['id']}")


def test_the_uploads_are_shown_apart_with_their_hashes(server, signed_in, finished):
    '''What went in, inspectable, with every artifact's hash: short in the
    table, whole on the page that looks inside it.'''
    upload = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'input' AND step IS NULL",
        (finished["id"],))
    text = page(signed_in, f"/portal/jobs/{finished['id']}/artifacts")

    assert "What was uploaded" in text and "the first" in text
    short = upload["digest"][:len("sha256:") + 12]
    assert short in text and f'title="{upload["digest"]}"' in text

    inside = signed_in.get(f"/portal/jobs/{finished['id']}/artifacts/{upload['id']}/inside")
    assert inside.status_code == 200
    assert upload["digest"] in inside.get_data(as_text=True)
    assert "gcd.pkg.json" in inside.get_data(as_text=True)     # the client's manifest


def test_an_upload_refused_as_unsafe_is_kept_and_never_opened(
        server, server_client, key, token, job_archive, dispatcher, signed_in,
        monkeypatch):
    '''Look-inside decompresses the whole archive -- the bomb it was refused
    for, on every click. The bytes are kept and the refusal shown instead.'''
    archive, digest, size = job_archive(extra={"../escape.txt": b"x"})
    job = stage(server_client, key, token, archive, size)
    assert slug(outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))) == \
        "archive-rejected"

    row = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND upload_seq = 1", (job["id"],))
    assert row is not None

    text = page(signed_in, f"/portal/jobs/{job['id']}/artifacts")
    assert "never opened" in text
    assert f"/artifacts/{row['id']}/inside" not in text

    def opened(*args, **kwargs):
        raise AssertionError("a refused upload was opened")

    monkeypatch.setattr(tarfile, "open", opened)
    inside = signed_in.get(f"/portal/jobs/{job['id']}/artifacts/{row['id']}/inside")
    assert inside.status_code == 200
    assert "refused before it was opened" in inside.get_data(as_text=True)


def test_the_artifacts_screen_lists_them_grouped_by_node(server, signed_in, finished, me):
    '''The listing is (items, cursor), and a template handed the tuple
    rendered an empty page once. Grouped by node, because the node is what a
    discard removes, with a node's inputs as their own row; deleting the job
    is here and not on the job page; a typed discard reason is labelled as
    public.'''
    inputs = node_root(server, me, finished, "steptwo") / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "gcd.vg").write_text("module gcd; endmodule\n")
    collect(server, me, finished, "steptwo", fresh=False)

    text = page(signed_in, f"/portal/jobs/{finished['id']}/artifacts")
    assert "what it was handed" in text

    assert "download" in text and "logs" in text
    assert "The run itself" in text
    assert "stepone/0" in text and "steptwo/0" in text
    assert text.count("Discard this node's output") == 2
    assert "/delete" in text
    assert "visible to everyone who can list this job" in text


def test_a_finished_jobs_page_draws_the_flow_and_opens_its_archives(
        server, signed_in, finished):
    '''Drawn on the server, not by a JavaScript graph library every release
    would pay for. `reports` there SHOWS the reports rather than download a
    tarball. It no longer refreshes: nothing is left to watch.'''
    text = page(signed_in, f"/portal/jobs/{finished['id']}")

    assert "<svg" in text
    assert 'class="wire"' in text
    assert text.count('class="node ') == 2
    assert f"/artifacts/{artifact_id(server, finished)}/inside" in text
    assert 'http-equiv="refresh"' not in text and "refresh now" not in text
    assert "/delete" not in text


def test_a_node_offers_every_log_it_wrote(signed_in, finished):
    '''SiliconCompiler's record and the TOOL's output answer different
    questions; a synthesis error is only in the second. SC's comes first.'''
    text = page(signed_in, f"/portal/jobs/{finished['id']}/logs/stepone/0")

    assert "sc_stepone_0.log" in text
    assert "stepone.log" in text
    assert "siliconcompiler says stepone" in text

    assert "the tool says stepone" in page(
        signed_in, f"/portal/jobs/{finished['id']}/logs/stepone/0?file=stepone.log")


def operator(server):
    store = server.config["SC_STORE"]
    return store, store.upsert_user("operator", "someone@host")["id"]


def test_software_can_be_retired_from_the_screen(signed_in, server):
    '''A version (*not this one*) and the software (*not any more*) are both
    retirable, or an operator cannot correct a mistake. A retired name offers
    no per-version button: retiring one would change nothing.'''
    from siliconcompiler.remote.server.software import images

    store, actor = operator(server)
    images.register_software(store, "yosys", "Yosys", actor, "tool")
    images.register_version(store, "yosys", "0.44", actor)
    images.register_version(store, "yosys", "0.45", actor)

    live = page(signed_in, "/portal/images")
    assert live.count("retire</button>") == 2
    assert "Stop curating" in live
    token = csrf(signed_in, "/portal/images")

    signed_in.post("/portal/images/software/yosys/retire",
                   data={"csrf": token, "version": "0.44"})
    assert store.one("SELECT retired_at FROM software_versions "
                     "WHERE software_name = 'yosys' AND version = '0.44'")["retired_at"]
    assert not store.one("SELECT retired_at FROM software "
                         "WHERE name = 'yosys'")["retired_at"]

    signed_in.post("/portal/images/software/yosys/retire", data={"csrf": token})
    assert store.one("SELECT retired_at FROM software "
                     "WHERE name = 'yosys'")["retired_at"]

    retired = page(signed_in, "/portal/images")
    assert "retire</button>" not in retired
    assert "Stop curating" not in retired


def test_a_version_nothing_reported_is_marked_on_the_screen(signed_in, server):
    '''A publish date (20260924) beats 2.0.1 under every comparison; the
    operator must see it can never satisfy a requirement, listed after the
    reported ones.'''
    from siliconcompiler.remote.server.software import images

    store, actor = operator(server)
    images.register_software(store, "magic", "Magic", actor, "tool")
    images.register_version(store, "magic", "20260924", actor, source="published_date")
    images.register_version(store, "magic", "8.3.2", actor)

    text = page(signed_in, "/portal/images")

    assert "no version reported" in text
    assert text.index("8.3.2") < text.index("20260924")


def test_the_operator_can_record_a_tool_that_reports_nothing(signed_in, server):
    signed_in.post("/portal/images/software",
                   data={"csrf": csrf(signed_in, "/portal/images"), "name": "magic",
                         "kind": "tool", "version": "20260924", "unversioned": "1"})

    assert server.config["SC_STORE"].one(
        "SELECT version_source FROM software_versions "
        "WHERE software_name = 'magic'")["version_source"] == "published_date"


def test_a_failed_jobs_page_says_why_and_offers_the_servers_records(
        server, server_client, key, token, job_archive, dispatcher, me, signed_in):
    '''A run that died before any node, every node `cancelled`. The frozen
    title, then the detail about this run; that no node failed, which is
    what an unreached node looks like; and the records it left -- the run log,
    the staging record and the diagnostics, with no `job.log` yet.'''
    from siliconcompiler.remote.server.running.dispatch import RUN_LOG

    job = submitted(server_client, key, token, job_archive)
    jobroot = server.config["SC_JOBS"].job_root(me, job["id"])
    (jobroot / RUN_LOG).write_text("Traceback (most recent call last):\n"
                                   "RuntimeError: git is required to import GitPython\n")
    write_progress(server, me, job, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:00:02.000Z",
        "error": "RuntimeError: git is required to import GitPython",
        "nodes": {"stepone/0": {"state": "cancelled"}, "steptwo/0": {"state": "cancelled"}}})
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    text = page(signed_in, f"/portal/jobs/{job['id']}")

    assert "The run failed" in text
    assert "git is required to import GitPython" in text
    assert "No node failed" in text
    assert "the job ended before that node started" in text
    assert "The job itself" in text and "download" in text
    assert ">Staging record</a>" in text
    assert ">diagnostics</a>" in text
    assert ">Job log</a>" not in text


def test_a_cancelled_job_is_not_told_nobody_cancelled_it(
        signed_in, server, server_client, key, token, job_archive, dispatcher, me):
    '''On a job somebody DID cancel, `cancelled` means what it looks like.'''
    job = running(server, server_client, key, token, job_archive, me)

    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)
    dispatcher.alive = False
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    text = page(signed_in, f"/portal/jobs/{job['id']}")
    assert "cancelled" in text
    assert "not\nthat anyone cancelled it" not in text
    assert "the job ended before that node started" not in text


def test_a_node_archive_is_browsed_one_member_at_a_time_by_name(signed_in, finished,
                                                                server):
    '''Report viewing needs a node's archive opened, with the whole thing
    still downloadable. A member is matched against the archive's own list,
    never joined into a path: the name is a query string.'''
    archive = artifact_id(server, finished)
    inside = f"/portal/jobs/{finished['id']}/artifacts/{archive}/inside"

    text = page(signed_in, inside)
    assert "sc_stepone_0.log" in text
    assert "Download all of it" in text
    assert f"/artifacts/{archive}\"" in text or f"/artifacts/{archive}'" in text

    assert "siliconcompiler says stepone" in page(signed_in, f"{inside}?file=sc_stepone_0.log")
    assert signed_in.get(f"{inside}?file=../../../etc/passwd").status_code == 404


def test_the_portal_shows_the_operators_diagnostics(signed_in, finished, server):
    '''Never fetchable over the API; an administrator (everyone, here) reads
    the scheduler's view of a node in the portal.'''
    row = artifact_id(server, finished, "diagnostics")

    assert "diagnostics" in page(signed_in, f"/portal/jobs/{finished['id']}/artifacts")
    text = page(signed_in,
                f"/portal/jobs/{finished['id']}/artifacts/{row}/inside?file=slurm.txt")
    assert "the scheduler&#39;s record of" in text or "the scheduler's record of" in text


def test_a_node_whose_scheduler_id_arrives_late_still_gets_its_diagnostics(
        server, server_client, key, token, job_archive, dispatcher, me, signed_in):
    '''Accounting lags, so the last node can have no id when the job is
    indexed (`simulate/0` on the rig). The job page's backfill keeps and
    indexes its record later, once however often it is read.'''
    job = submitted(server_client, key, token, job_archive)
    for step in ("stepone", "steptwo"):
        node_root(server, me, job, step).mkdir(parents=True, exist_ok=True)
    write_progress(server, me, job, COMPLETED)

    everything = dispatcher.node_jobs
    dispatcher.node_jobs = lambda job_id, nodes: {
        node: name for node, name in everything(job_id, nodes).items()
        if node != ("steptwo", "0")}
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    def diagnostics(step):
        return server.config["SC_STORE"].all(
            "SELECT id FROM artifacts WHERE job_id = ? AND kind = ? AND step = ?",
            (job["id"], "diagnostics", step))

    assert len(diagnostics("stepone")) == 1 and diagnostics("steptwo") == []

    dispatcher.node_jobs = everything
    for _ in range(2):
        server.config["SC_JOBS"]._asked.clear()           # the throttle's floor passed
        signed_in.get(f"/portal/jobs/{job['id']}")

    (late,) = diagnostics("steptwo")
    text = page(signed_in, f"/portal/jobs/{job['id']}/artifacts/{late['id']}/inside"
                           "?file=slurm.txt")
    assert f"record of {job['id']}_steptwo_0" in text


def test_a_link_in_an_archive_is_never_followed(signed_in, finished, server, me):
    '''Only a regular member is served: a kept link would be a second name
    for anything in the archive, and nothing is served by alias.'''
    node = node_root(server, me, finished)
    (node / "outputs").mkdir(exist_ok=True)
    (node / "alias.log").symlink_to("outputs")
    collect(server, me, finished)

    row = server.config["SC_STORE"].one(
        "SELECT id, storage_key FROM artifacts WHERE job_id = ? AND kind = 'node' "
        "AND step = 'stepone'", (finished["id"],))
    with tarfile.open(server.config["SC_STORAGE"].artifact_path(row["storage_key"])) as tar:
        assert tar.getmember("alias.log").issym()          # kept: it stays inside

    inside = f"/portal/jobs/{finished['id']}/artifacts/{row['id']}/inside"
    assert "alias.log" not in page(signed_in, inside)
    assert signed_in.get(f"{inside}?file=alias.log").status_code == 404
    assert signed_in.get(f"{inside}?file=alias.log&raw=1").status_code == 404


def test_the_raw_route_never_serves_html(signed_in, finished, server, me):
    '''An artifact is bytes a JOB made; as text/html from this origin a
    design's own script would run on the portal.'''
    (node_root(server, me, finished) / "trouble.html").write_text("<script>alert(1)</script>")
    collect(server, me, finished)

    response = signed_in.get(f"/portal/jobs/{finished['id']}/artifacts/"
                             f"{artifact_id(server, finished)}/inside?file=trouble.html&raw=1")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_delete_needs_the_job_named(signed_in, finished):
    '''A speed bump, not a security control (CSRF is that): the button sat
    one position from the link people click constantly.'''
    token = csrf(signed_in, f"/portal/jobs/{finished['id']}/artifacts")

    refused = signed_in.post(f"/portal/jobs/{finished['id']}/delete",
                             data={"csrf": token, "confirm": "something else"})
    assert refused.status_code == 400

    accepted = signed_in.post(f"/portal/jobs/{finished['id']}/delete",
                              data={"csrf": token, "confirm": "gcd/job0"})
    assert accepted.status_code == 302


def test_the_portal_is_the_way_past_the_download_ceiling(signed_in, finished,
                                                         server, server_client,
                                                         key, token):
    '''`max_download_bytes` has no API override, so without the portal an
    object over it is unreachable by its owner. A browser download is a person
    choosing one object; the ceiling stops an automated sweep.'''
    row = artifact_id(server, finished)
    server.config["SC_CONFIG"].limits["max_download_bytes"] = 1

    assert call(server_client, key, "GET",
                f"/v1/jobs/{finished['id']}/artifacts/{row}", token).status_code == 403

    response = signed_in.get(f"/portal/jobs/{finished['id']}/artifacts/{row}")
    assert response.status_code == 302
    assert signed_in.get(response.headers["Location"]).status_code == 200
    # Browsing reads one bounded member rather than the whole thing.
    assert signed_in.get(
        f"/portal/jobs/{finished['id']}/artifacts/{row}/inside").status_code == 200


def test_the_account_page_shows_each_ceiling_beside_its_default(signed_in, server, me):
    '''Two columns: one value says neither *is this mine* nor *what would
    it be otherwise*. Read-only, as this deployment has no admin mode.
    `max_staging_seconds` is the deployment's alone.'''
    import re

    from siliconcompiler.remote.server.identity import accounts

    accounts.set_limit(server.config["SC_STORE"], me, "max_download_bytes",
                       1024, me, note="a slow link")

    text = page(signed_in, "/portal/account")

    assert "max_download_bytes" in text
    assert "1.0 KiB" in text                       # what this account gets
    assert "100 MiB" in text                       # what the deployment gives
    assert "set for you" in text
    assert "portal.set_limit" not in text
    row = re.search(r'<td class="mono">max_staging_seconds</td>\s*'
                    r'<td class="mono">([^<]*)</td>', text)
    assert row and row.group(1) == str(server.config["SC_CONFIG"].limits["max_staging_seconds"])


def test_the_nodes_table_is_in_the_order_the_run_reaches_them():
    '''The API lists nodes by name, which puts `elaborate` mid-asicflow.
    Ties break on the name, so a reload never reshuffles the rows.'''
    from siliconcompiler.remote.server.portal import running_order

    job = {"nodes": [{"step": "zzz_last", "index": "0"}, {"step": "aaa_middle", "index": "0"},
                     {"step": "mmm_first", "index": "0"}]}
    edges = [{"from_step": "mmm_first", "from_index": "0",
              "to_step": "aaa_middle", "to_index": "0"},
             {"from_step": "aaa_middle", "from_index": "0",
              "to_step": "zzz_last", "to_index": "0"}]

    assert [n["step"] for n in running_order(job, edges)] == [
        "mmm_first", "aaa_middle", "zzz_last"]

    job = {"nodes": [{"step": "b", "index": "1"}, {"step": "b", "index": "0"},
                     {"step": "a", "index": "0"}]}
    assert [(n["step"], n["index"]) for n in running_order(job, [])] == [
        ("a", "0"), ("b", "0"), ("b", "1")]


def test_a_cold_link_to_a_job_comes_back_to_that_job(server_client, key, token,
                                                     finished):
    '''Otherwise "here is your job" answered "here is a list, find it".'''
    job_page = f"/portal/jobs/{finished['id']}"

    turned_away = server_client.get(job_page)
    assert turned_away.status_code == 401
    assert "sc-remote -portal" in turned_away.get_data(as_text=True)

    entered = enter(server_client, browser(server_client, key, token))
    assert entered.status_code == 302
    assert entered.headers["Location"].endswith(job_page)


def test_the_return_path_is_never_an_open_redirect(server_client, key, token):
    '''Anything can set a cookie on this origin, and a redirect following
    one is the classic phishing primitive -- on the trusted way in.'''
    response = browser(server_client, key, token)

    for hostile in ("//evil.example/", "https://evil.example/",
                    "/etc/passwd", "/v1/jobs"):
        server_client.set_cookie("sc_portal_next", hostile, domain="localhost")
        entered = enter(server_client, response)
        if entered.status_code == 302:
            assert "evil.example" not in entered.headers["Location"]
            assert entered.headers["Location"].rstrip("/").endswith("/portal")
        # A spent handover is also an acceptable answer here.
        server_client.delete_cookie("sc_portal_next", domain="localhost")


def test_only_a_job_still_going_refreshes_and_it_cannot_be_archived(
        server_client, key, token, job_archive, dispatcher, signed_in, finished):
    '''`<meta http-equiv="refresh">`: stops with the tab, works without
    scripting. A queued job holds a slot and a created one an upload grant,
    so hiding one still going makes "why can I not submit" unanswerable.'''
    assert 'http-equiv="refresh"' not in page(signed_in, "/portal/")

    job = submitted(server_client, key, token, job_archive)

    busy = page(signed_in, "/portal/")
    assert 'http-equiv="refresh"' in busy
    assert "1 still going" in busy
    assert job["id"][:8] in busy

    text = page(signed_in, f"/portal/jobs/{job['id']}")
    assert 'http-equiv="refresh"' in text and "refresh now" in text

    refused = signed_in.post(f"/portal/jobs/{job['id']}/archive",
                             data={"csrf": csrf(signed_in, f"/portal/jobs/{job['id']}"),
                                   "archived": "1"})
    assert refused.status_code == 409


def test_discarding_the_output_keeps_the_job(signed_in, finished, server):
    '''Deleting the JOB takes it out of the collection -- far more than
    reclaiming a finished run's space. The rows stay, saying the bytes went.'''
    token = csrf(signed_in, f"/portal/jobs/{finished['id']}/artifacts")

    done = signed_in.post(f"/portal/jobs/{finished['id']}/discard",
                          data={"csrf": token, "confirm": "gcd/job0"})
    assert done.status_code == 302

    store = server.config["SC_STORE"]
    assert store.one("SELECT deleted_at FROM jobs WHERE id = ?",
                     (finished["id"],))["deleted_at"] is None
    assert finished["id"] in page(signed_in, "/portal/")
    assert signed_in.get(f"/portal/jobs/{finished['id']}").status_code == 200

    rows = store.all("SELECT deleted_at, deleted_reason FROM artifacts WHERE job_id = ?",
                     (finished["id"],))
    assert rows and all(r["deleted_at"] for r in rows)
    assert all(r["deleted_reason"].startswith("discarded by ") for r in rows)


def test_a_typed_discard_reason_is_kept_on_one_line(signed_in, finished, server):
    '''`deleted_reason` is read by everyone who can list the job.'''
    signed_in.post(f"/portal/jobs/{finished['id']}/discard",
                   data={"csrf": csrf(signed_in, f"/portal/jobs/{finished['id']}/artifacts"),
                         "confirm": "gcd/job0",
                         "reason": "  freeing space\nbefore the tapeout  "})

    rows = server.config["SC_STORE"].all(
        "SELECT deleted_reason FROM artifacts WHERE job_id = ?", (finished["id"],))
    assert rows and all(r["deleted_reason"] == "freeing space before the tapeout"
                        for r in rows)


def test_the_node_is_the_unit_of_deletion(signed_in, finished, server, me):
    '''A node's logs, reports and archive are rows over ONE set of bytes,
    so they go together, with the tree they were indexed from. The operators'
    diagnostics stay, as do the other node, the job and its own objects; a
    node the job does not have is a 404.'''
    store = server.config["SC_STORE"]
    assert node_root(server, me, finished).is_dir()
    token = csrf(signed_in, f"/portal/jobs/{finished['id']}/artifacts")

    for step, status in (("nope", 404), ("stepone", 302)):
        done = signed_in.post(f"/portal/jobs/{finished['id']}/discard-node",
                              data={"csrf": token, "step": step, "index": "0"})
        assert done.status_code == status

    rows = store.all('SELECT kind, deleted_at, deleted_reason FROM artifacts '
                     'WHERE job_id = ? AND step = ? AND "index" = ?',
                     (finished["id"], "stepone", "0"))
    kept = [row for row in rows if row["kind"] == "diagnostics"]
    gone = [row for row in rows if row["kind"] != "diagnostics"]
    assert {row["kind"] for row in gone} == {"logs", "node"}
    assert all(row["deleted_at"] for row in gone)
    assert all(row["deleted_reason"].startswith("discarded by ") for row in gone)
    assert kept and not any(row["deleted_at"] for row in kept)

    for where, args in (("step = ?", ("steptwo",)), ("step IS NULL", ())):
        others = store.all(f"SELECT deleted_at FROM artifacts WHERE job_id = ? AND {where}",
                           (finished["id"], *args))
        assert others and not any(row["deleted_at"] for row in others)
    assert store.one("SELECT deleted_at FROM jobs WHERE id = ?",
                     (finished["id"],))["deleted_at"] is None

    assert not node_root(server, me, finished).exists()
    assert node_root(server, me, finished, "steptwo").is_dir()


def test_archiving_hides_a_job_from_the_default_list_and_nothing_else(
        signed_in, finished):
    '''A view preference: a direct read and every subresource still work,
    and there is a way back.'''
    token = csrf(signed_in, f"/portal/jobs/{finished['id']}")

    signed_in.post(f"/portal/jobs/{finished['id']}/archive",
                   data={"csrf": token, "archived": "1"})

    assert finished["id"] not in page(signed_in, "/portal/")
    assert finished["id"] in page(signed_in, "/portal/?archived=true")
    assert signed_in.get(f"/portal/jobs/{finished['id']}").status_code == 200

    signed_in.post(f"/portal/jobs/{finished['id']}/archive",
                   data={"csrf": token, "archived": "0"})
    assert finished["id"] in page(signed_in, "/portal/")
