import json
import sqlite3

from pathlib import Path

import pytest

from siliconcompiler import __version__ as sc_version
from siliconcompiler.remote.server.errors import ERRORS, TYPE_BASE, problem, ProblemError
from siliconcompiler.remote.server.ids import uuid7
from siliconcompiler.remote.server.store import now


pytest.importorskip("flask", reason="the server extra is not installed")


# These run against app.test_client(): an in-process WSGI client with no port,
# no event loop and no teardown. Seventeen of this profile's eighteen endpoints
# are request-in, response-out, so this is the shape almost every server test
# takes.


@pytest.fixture
def server():
    '''A server on a datadir that has never been used.

    No config file is written: a bare datadir has to start and serve a complete
    GET /v1, which is what makes the defaults load-bearing rather than a
    convenience.
    '''
    from siliconcompiler.remote.server.app import create_app

    return create_app("datadir")


@pytest.fixture
def client(server):
    return server.test_client()


###########################
# Endpoint 1: GET /v1
###########################

def test_capabilities_are_served(client):
    resp = client.get("/v1")

    assert resp.status_code == 200
    assert resp.mimetype == "application/json"
    assert resp.get_json()["api_version"] == "v1"


def test_every_required_member_is_real(client):
    '''The one endpoint whose every field must be real on day one.'''
    body = client.get("/v1").get_json()

    assert set(body) == {"api_version", "software", "grant_types_supported",
                         "limits", "features", "identity_assurance", "notices"}

    assert body["identity_assurance"] == "self-asserted"
    assert body["notices"] == []
    # Both are served: the archived file and the live tail. Two strings,
    # because one could not say which of the two a deployment had.
    assert body["features"] == ["logs", "logs.stream"]


def test_the_device_grant_is_not_advertised(client):
    '''grant_types_supported is what the client branches on, never
    identity_assurance. This profile logs in with no browser and no human.'''
    body = client.get("/v1").get_json()

    assert body["grant_types_supported"] == ["client_credentials", "refresh_token"]
    assert "urn:ietf:params:oauth:grant-type:device_code" \
        not in body["grant_types_supported"]


def test_projects_are_not_a_feature(client):
    '''"projects" is never in features here; naming one anywhere is refused with
    feature-unsupported.'''
    assert "projects" not in client.get("/v1").get_json()["features"]


def test_every_limit_is_a_base_unit(client):
    """Bytes are never MB and a count is never a duration: the refusal that
    names a key back spells it identically, which is what makes the error
    registry double as the enforcement trace."""
    limits = client.get("/v1").get_json()["limits"]

    assert set(limits) == {
        "max_job_nodes", "max_upload_bytes", "job_retention_days",
        "pending_uploads", "concurrent_jobs", "concurrent_log_streams",
        "max_log_stream_seconds", "max_archive_members",
        "max_archive_expanded_bytes", "auto_fetch_max_bytes"}
    assert all(isinstance(value, int) for value in limits.values())


def test_terms_url_is_absent_rather_than_null(client):
    '''OPTIONAL, and absent is not empty: emitting null would say something
    different from saying nothing.'''
    assert "terms_url" not in client.get("/v1").get_json()


def test_software_falls_back_to_this_server_when_no_image_is_registered(client):
    '''A deployment that runs no containers is conforming, and what it runs is
    the SiliconCompiler this process was installed with.'''
    assert client.get("/v1").get_json()["software"] == {
        "siliconcompiler": [sc_version]}


def test_a_registered_image_takes_over_from_the_fallback(server, client):
    '''Once an operator is curating a registry, the join governs.'''
    store = server.config["SC_STORE"]
    user = store.upsert_user("local", "operator")

    store.execute("INSERT INTO software (name, display_name, added_by) "
                  "VALUES ('siliconcompiler', 'SiliconCompiler', ?)", (user["id"],))
    store.execute("INSERT INTO software_versions "
                  "(software_name, version, added_by) "
                  "VALUES ('siliconcompiler', '9.9.9', ?)", (user["id"],))

    image = str(uuid7())
    store.execute(
        "INSERT INTO images (id, registry_ref, digest, resolved_at, registered_by) "
        "VALUES (?, 'ghcr.io/x/y:9.9.9', 'sha256:dd', ?, ?)",
        (image, now(), user["id"]))
    store.execute("INSERT INTO image_contents (image_id, software_name, version) "
                  "VALUES (?, 'siliconcompiler', '9.9.9')", (image,))

    assert client.get("/v1").get_json()["software"] == {
        "siliconcompiler": ["9.9.9"]}


###########################
# Endpoint 2: GET /v1/healthz
###########################

def test_healthz_passes(client):
    resp = client.get("/v1/healthz")

    assert resp.status_code == 200
    assert resp.mimetype == "application/health+json"
    assert resp.headers["Cache-Control"] == "no-store"


def test_healthz_says_as_little_as_it_can(client):
    '''status is REQUIRED and is the ONLY member.

    This endpoint takes no credential, so a diagnostic string here tells anyone
    who can reach the deployment what is broken inside it -- and a version
    string tells them what to look up. The reason a server is degraded goes to
    the log, which has an entitled reader.
    '''
    body = client.get("/v1/healthz").get_json()

    assert body == {"status": "pass"}
    assert sc_version not in json.dumps(body)


def test_healthz_reads_the_store_rather_than_a_constant(server, monkeypatch):
    '''`SELECT 1` is evaluated without touching the database, so it would
    answer pass for a store that had been deleted out from under the process.
    '''
    store = server.config["SC_STORE"]

    def unreachable(sql, params=()):
        raise sqlite3.OperationalError("database disk image is malformed")

    monkeypatch.setattr(store, "one", unreachable)

    resp = server.test_client().get("/v1/healthz")

    assert resp.status_code == 503
    assert resp.get_json() == {"status": "fail"}


def test_a_degraded_store_reports_fail_rather_than_raising(server, monkeypatch):
    '''A liveness probe answers; it does not hand a load balancer a 500 page.'''
    store = server.config["SC_STORE"]
    monkeypatch.setattr(store, "one", lambda sql, params=(): {"n": 0})

    resp = server.test_client().get("/v1/healthz")

    assert resp.status_code == 503
    assert resp.get_json()["status"] == "fail"


def test_downtime_is_announced_on_capabilities_not_on_the_probe(client):
    '''An announcement is read once, by a person, at the start of a session;
    the probe is scraped every few seconds by a load balancer.'''
    assert "notices" in client.get("/v1").get_json()
    assert "notices" not in client.get("/v1/healthz").get_json()


def test_the_two_unauthenticated_endpoints_are_the_caching_exceptions(client):
    '''Everything else carries private, no-store: a cache rule that ever
    matched /v1/* would serve one caller's response to another's request.'''
    assert "max-age" in client.get("/v1").headers["Cache-Control"]
    assert client.get("/v1/healthz").headers["Cache-Control"] == "no-store"


###########################
# Config
###########################

def test_a_config_file_overrides_one_limit_and_keeps_the_rest():
    from siliconcompiler.remote.server.app import create_app

    Path("datadir").mkdir()
    Path("datadir/config.json").write_text(json.dumps(
        {"limits": {"concurrent_jobs": 1}, "notices": ["back at 09:00"]}))

    body = create_app("datadir").test_client().get("/v1").get_json()

    assert body["limits"]["concurrent_jobs"] == 1
    assert body["limits"]["max_job_nodes"] == 1000
    assert body["notices"] == ["back at 09:00"]


def test_a_misspelled_config_key_is_refused_rather_than_ignored():
    '''A key that silently does nothing is a ceiling the operator believes they
    set.'''
    from siliconcompiler.remote.server.app import create_app

    Path("datadir").mkdir()
    Path("datadir/config.json").write_text(json.dumps({"limitz": {}}))

    with pytest.raises(ValueError, match="unknown keys: limitz"):
        create_app("datadir")


def test_a_misspelled_limit_is_refused_too():
    from siliconcompiler.remote.server.app import create_app

    Path("datadir").mkdir()
    Path("datadir/config.json").write_text(json.dumps(
        {"limits": {"concurrent_job": 1}}))

    with pytest.raises(ValueError, match="unknown limits: concurrent_job"):
        create_app("datadir")


def test_terms_url_is_published_when_an_operator_sets_one():
    from siliconcompiler.remote.server.app import create_app

    Path("datadir").mkdir()
    Path("datadir/config.json").write_text(json.dumps(
        {"terms_url": "https://example.com/terms"}))

    body = create_app("datadir").test_client().get("/v1").get_json()

    assert body["terms_url"] == "https://example.com/terms"


###########################
# Persistence
###########################

def test_the_store_survives_a_restart(client):
    '''The defect this store exists to fix: a restart used to lose every
    running job, and finished jobs were never remembered at all.'''
    from siliconcompiler.remote.server.app import create_app

    first = client.get("/v1").get_json()

    restarted = create_app("datadir").test_client().get("/v1").get_json()

    assert restarted == first
    assert Path("datadir/server.db").exists()


def test_storage_is_a_file_uri_under_the_datadir(server):
    '''A location is a row and uri_base is a URI, so file:// is a first-class
    deployment rather than a second shape.'''
    store = server.config["SC_STORE"]
    location = store.one("SELECT * FROM storage_locations")

    assert location["id"] == "primary"
    assert location["uri_base"].startswith("file:///")
    assert location["uri_base"].endswith("/artifacts/")
    assert location["writable"] == 1


###########################
# Errors
###########################

def test_the_registry_is_the_frozen_thirty_one():
    '''Frozen at v1, and the namespace is SiliconCompiler's rather than any one
    deployment's: both implementations must return the same URI or a client
    cannot branch across them.'''
    assert len(ERRORS) == 31
    assert all(err.uri == f"{TYPE_BASE}/{slug}" for slug, err in ERRORS.items())


def test_the_three_that_are_never_http_responses():
    '''These are `type` values on a job's or a node's error object.'''
    assert {slug for slug, err in ERRORS.items() if err.status is None} == {
        "scheduler-lost", "run-failed"}

    with pytest.raises(ValueError, match="never an HTTP response"):
        ProblemError("run-failed")


def test_a_slug_outside_the_registry_cannot_be_raised():
    '''An implementation that mints its own slug costs a client a second
    table.'''
    with pytest.raises(KeyError):
        ProblemError("made-up-condition")


def test_the_discriminator_is_a_member_not_the_slug():
    '''A slug names a kind of failure, never one instance of it: a member's
    value can be added after the freeze and a slug cannot.'''
    body = problem("limit-exceeded", detail="four already running",
                   limit="concurrent_jobs")

    assert body["type"] == f"{TYPE_BASE}/limit-exceeded"
    assert body["limit"] == "concurrent_jobs"
    assert body["status"] == 429


def test_an_unrouted_path_is_problem_json(client):
    resp = client.get("/v1/nothing-here")

    assert resp.status_code == 404
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["type"] == f"{TYPE_BASE}/not-found"


def test_a_wrong_method_carries_allow(client):
    '''RFC 9110 requires the header; a bare 405 is non-conforming.'''
    resp = client.post("/v1")

    assert resp.status_code == 405
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["type"] == f"{TYPE_BASE}/method-not-allowed"
    assert "GET" in resp.headers["Allow"]


def test_a_raised_problem_renders_with_its_members(server):
    '''Raised where it is decided, rendered at the edge.'''
    import flask

    @server.route("/v1/_boom")
    def boom():
        raise ProblemError("feature-unsupported",
                           detail="this deployment does not do device grants",
                           feature="device_grant")

    resp = server.test_client().get("/v1/_boom")

    assert resp.status_code == 501
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json() == {
        "type": f"{TYPE_BASE}/feature-unsupported",
        "title": "This deployment does not support that",
        "status": 501,
        "detail": "this deployment does not do device grants",
        "feature": "device_grant",
    }
    assert flask is not None


###########################
# The command line
###########################

def test_help_works_without_the_server_extra(capsys, monkeypatch):
    '''The module entry point is importable whether or not the extra is, and
    the docs build renders the apps reference from exactly this.'''
    from siliconcompiler.remote.server import __main__ as entry

    with pytest.raises(SystemExit) as exit_code:
        entry.main(["--help"])

    assert exit_code.value.code == 0
    assert "-datadir" in capsys.readouterr().out


def test_running_without_the_server_extra_is_a_message_not_a_traceback(
        capsys, monkeypatch):
    from siliconcompiler.remote.server import app as app_module
    from siliconcompiler.remote.server import __main__ as entry

    monkeypatch.setattr(app_module, "missing_server_dependency", "flask")

    assert entry.main([]) == 1

    err = capsys.readouterr().err
    assert "the server is unavailable" in err
    assert 'pip install "siliconcompiler[server]"' in err


def test_three_flags_and_their_defaults():
    '''Fewer arguments is the point: everything else has a default and can be
    overridden in <datadir>/config.json.'''
    from siliconcompiler.remote.server import __main__ as entry

    args = entry._parser().parse_args([])

    assert args.port == 8080
    assert args.cluster == "local"
    assert args.datadir == "./sc_server"

    assert {action.dest for action in entry._parser()._actions} == {
        "help", "port", "datadir", "cluster", "version"}


def test_a_broken_config_is_reported_and_exits_non_zero(caplog):
    '''A setup problem gets the one line that says which, not a traceback.'''
    from siliconcompiler.remote.server import __main__ as entry

    Path("datadir").mkdir()
    Path("datadir/config.json").write_text("{not json")

    assert entry.main(["-datadir", "datadir"]) == 1
