import json
import sqlite3
import sys
import uuid

from pathlib import Path

import pytest

from siliconcompiler import __version__ as sc_version
from siliconcompiler.remote.server.errors import ERRORS, TYPE_BASE, problem, ProblemError
from siliconcompiler.remote.server.state.store import now


pytest.importorskip("flask", reason="the server extra is not installed")


# Against app.test_client(): in-process, no port, no event loop -- the shape of
# seventeen of this profile's eighteen endpoints.

HOST_PYTHON = "%d.%d.%d" % sys.version_info[:3]
FALLBACK_SOFTWARE = {"python": {"siliconcompiler": [sc_version]}, "tools": {},
                     "interpreter": {"python": [HOST_PYTHON]}}


@pytest.fixture
def client(server_client):
    '''A server on a datadir never used: no config file, so the defaults are
    load-bearing.'''
    return server_client


def write_config(values):
    Path("datadir").mkdir()
    Path("datadir/config.json").write_text(json.dumps(values))
    return "datadir"


def create_app(datadir):
    from siliconcompiler.remote.server.app import create_app

    return create_app(datadir)


def test_get_v1_is_complete_on_a_bare_datadir(client):
    '''The one endpoint whose every field is real on day one. Two feature
    strings, since one could not say whether a deployment serves the archive
    or the live tail; `grant_types_supported`, not `identity_assurance`, is
    what a client branches on, so the device grant is not in it. Every limit
    is a base unit, spelled as the refusal naming it is. `terms_url` is
    absent rather than null. With no image registered, `software` is this
    process's SiliconCompiler and Python.'''
    resp = client.get("/v1")

    assert resp.status_code == 200
    assert resp.mimetype == "application/json"
    assert "max-age" in resp.headers["Cache-Control"]
    body = resp.get_json()
    assert set(body) == {"api_version", "software", "grant_types_supported",
                         "limits", "features", "identity_assurance", "notices"}
    assert body["api_version"] == "v1"
    assert body["identity_assurance"] == "self_asserted"
    assert body["notices"] == []
    assert body["features"] == ["logs.stream", "logs.stream.job"]     # never "projects"
    assert body["grant_types_supported"] == ["client_credentials", "refresh_token"]
    assert set(body["limits"]) == {
        "max_job_nodes", "max_upload_bytes", "artifact_retention_seconds",
        "max_staging_seconds", "pending_uploads", "concurrent_jobs", "concurrent_log_streams",
        "max_archive_members", "max_archive_expanded_bytes", "max_download_bytes",
        "abandon_after_seconds"}
    assert all(isinstance(value, int) for value in body["limits"].values())
    assert body["limits"]["artifact_retention_seconds"] == 2592000      # thirty days
    assert body["software"] == FALLBACK_SOFTWARE


def test_only_this_servers_own_siliconcompiler_is_advertised(server, client):
    '''🔴 One version, the one this server runs, whatever the registry tracks
    (profile §5): the manifest's read is this server's SiliconCompiler.'''
    store = server.config["SC_STORE"]
    user = store.upsert_user("local", "operator")
    store.execute("INSERT INTO software (name, display_name, kind, added_by) "
                  "VALUES ('siliconcompiler', 'SiliconCompiler', 'python', ?)", (user["id"],))
    store.execute("INSERT INTO software_versions (software_name, version, added_by) "
                  "VALUES ('siliconcompiler', '9.9.9', ?)", (user["id"],))
    image = str(uuid.uuid4())
    store.execute(
        "INSERT INTO images (id, registry_ref, digest, resolved_at, registered_by) "
        "VALUES (?, 'ghcr.io/x/y:9.9.9', 'sha256:dd', ?, ?)", (image, now(), user["id"]))
    store.execute("INSERT INTO image_contents (image_id, software_name, version) "
                  "VALUES (?, 'siliconcompiler', '9.9.9')", (image,))

    assert client.get("/v1").get_json()["software"] == FALLBACK_SOFTWARE


def test_healthz_says_pass_and_nothing_more(client):
    '''`status` is the ONLY member: with no credential, a diagnostic or a
    version tells anyone what to look up. Notices are on capabilities.'''
    resp = client.get("/v1/healthz")

    assert resp.status_code == 200
    assert resp.mimetype == "application/health+json"
    assert resp.headers["Cache-Control"] == "no-store"
    assert resp.get_json() == {"status": "pass"}


def _unreachable(sql, params=()):
    raise sqlite3.OperationalError("database disk image is malformed")


@pytest.mark.parametrize("one", [_unreachable, lambda sql, params=(): {"n": 0}],
                         ids=["unreachable", "degraded"])
def test_a_broken_store_fails_the_probe_rather_than_raising(server, monkeypatch, one):
    '''`SELECT 1` never touches the database, so the probe reads the store, and
    answers a load balancer rather than handing it a 500 page.'''
    monkeypatch.setattr(server.config["SC_STORE"], "one", one)

    resp = server.test_client().get("/v1/healthz")

    assert resp.status_code == 503
    assert resp.get_json() == {"status": "fail"}


def test_a_detail_never_carries_more_than_a_line_of_borrowed_text():
    '''🔴 A tool's exception or a member's name can carry a path the CLIENT
    chose, so the bound is in `problem()`, not at each call site.'''
    from siliconcompiler.remote.server.errors import DETAIL_MAX

    body = problem("invalid-request", detail="/a/path " * 200)

    assert len(body["detail"]) <= DETAIL_MAX + 3       # the ellipsis
    assert body["detail"].endswith("...")


@pytest.mark.parametrize("said,kept", [
    ("first line\n\tsecond\x1b[31m red \x00", "first line second[31m red"),
    # C1 too: U+009B is a terminal's escape in one character.
    ("a\x1b[2Jb\x9b31mc\x07d\x85e", "a[2Jb31mcde"),
])
def test_a_detail_is_one_line_with_no_terminal_control(said, kept):
    '''It is printed to a terminal and read back out of a log.'''
    assert problem("invalid-request", detail=said)["detail"] == kept


@pytest.fixture
def internals(monkeypatch):
    '''What this server would not say about itself, for one test.'''
    from siliconcompiler.remote.server import errors

    monkeypatch.setattr(errors, "_INTERNAL_PATHS", [])
    monkeypatch.setattr(errors, "_INTERNAL_NAMES", [])
    errors.set_internals(paths=["/srv/sc/datadir", "/opt/foundry", "/"],
                         names=["compute-07.cluster.internal", "compute-07"])
    return errors


def test_a_detail_says_nothing_of_the_servers_own_layout(internals):
    '''🔴 D122: a tool's exception carries mount paths and hostnames.'''
    body = internals.problem(
        "invalid-request",
        detail="cannot open /srv/sc/datadir/users/u1/builds/j/x.v on "
               "compute-07.cluster.internal (compute-07): /opt/foundry/pdk missing")

    assert body["detail"] == ("cannot open <server>/users/u1/builds/j/x.v on <host> "
                              "(<host>): <server>/pdk missing")


@pytest.mark.parametrize("said,kept", [
    ("fetch failed: token=ghp_abc123", "token=<redacted>"),
    ("Authorization: Bearer abc.def", "Authorization <redacted>"),
    ("sent DPoP abc.def", "DPoP <redacted>"),
    ("https://user:hunter2@git.example.com/x", "https://<redacted>@git.example.com/x"),
    ("key ghp_" + "a" * 36 + " rejected", "key <redacted> rejected"),
])
def test_a_detail_says_nothing_credential_shaped(internals, said, kept):
    detail = internals.problem("invalid-request", detail=said)["detail"]

    assert kept in detail
    assert not any(secret in detail for secret in ("hunter2", "ghp_", "abc"))


def test_the_detail_bound_binds_and_is_not_published():
    '''No client acts on it, so it stays off the wire. ⚠️ Characters, not
    bytes: truncating UTF-8 by byte count splits a codepoint.'''
    from siliconcompiler.remote.server import errors

    app = create_app(write_config({"limits": {"max_detail_chars": 40}}))

    assert "max_detail_chars" not in app.test_client().get("/v1").get_json()["limits"]
    assert len(errors.bound("x" * 500)) <= 43          # 40 plus the ellipsis


def test_a_config_file_overrides_what_it_names_and_keeps_the_rest():
    '''A notice's `starts_at` and `ends_at` are REQUIRED and nullable. It is
    published until `ends_at` passes: `starts_at` is when the event starts,
    so next week's downtime is published now.'''
    plain = {"level": "info", "message": "back at 09:00"}
    over = {"level": "warning", "message": "was down", "starts_at": None,
            "ends_at": "2020-01-01T00:00:00Z"}
    coming = {"level": "warning", "message": "down next week",
              "starts_at": "2099-01-01T02:00:00Z", "ends_at": "2099-01-01T06:00:00.500Z"}

    body = create_app(write_config({
        "limits": {"concurrent_jobs": 1}, "notices": [plain, over, coming],
        "terms_url": "https://example.com/terms"})).test_client().get("/v1").get_json()

    assert body["limits"]["concurrent_jobs"] == 1
    assert body["limits"]["max_job_nodes"] == 1000
    assert body["notices"] == [dict(plain, starts_at=None, ends_at=None), coming]
    assert body["terms_url"] == "https://example.com/terms"


def _notice(**members):
    return {"notices": [dict({"level": "info", "message": "x"}, **members)]}


@pytest.mark.parametrize("values,complaint", [
    # A key that silently does nothing is a ceiling the operator believes set.
    ({"limitz": {}}, "unknown keys: limitz"),
    ({"limits": {"concurrent_job": 1}}, "unknown limits: concurrent_job"),
    # 🔴 `features` is a registry: a client would rely on what nothing serves.
    ({"features": ["logs.stream", "python-env"]}, "python-env, which is not a registered"),
    # `-1` is the store's spelling of unlimited, never the wire's.
    ({"limits": {"max_upload_bytes": -1}}, "max_upload_bytes"),
    # Null is unlimited only where the server compares against it as such.
    ({"limits": {"max_job_nodes": None}}, "limits.max_job_nodes may not be null"),
    ({"limits": {"concurrent_log_streams": None}},
     "limits.concurrent_log_streams may not be null"),
    ({"limits": {"max_upload_bytes": None}}, "limits.max_upload_bytes may not be null"),
    # Surface §14: one PUT, no resume.
    ({"storage_uri_base": "s3://bucket/artifacts/",
      "limits": {"max_upload_bytes": 6 * 1024 ** 3}}, "one PUT"),
    ({"fetch_allowlist": ["https://*/"]}, "leftmost label"),
    ({"api_fetchable_kinds": ["manifest", "gds"]}, "unknown kinds: gds"),
    ({"denied_resources": {"pdks": ["x"]}}, "unknown resource kinds: pdks"),
    ({"denied_resources": {"pdk": "GF180*"}}, "must be a list"),
    (_notice(level="urgent"), "level"),
    (_notice(message=""), "1 to 500"),
    (_notice(message="x" * 501), "1 to 500"),
    (_notice(audience="all"), "audience"),
    (_notice(ends_at="Saturday"), "ends_at"),
    (_notice(starts_at="2026-09-27T02:00:00+01:00"), "starts_at"),
    ({"notices": ["maintenance on Sunday"]}, "a notice is"),
    # Private dataroots keep a library's, a tool's and a task's apart.
    ({"private_dataroots": {"acme_pdk": {"acme_pdk": "/opt/pdks/acme"}}},
     "is none of library, tool and task"),
    ({"private_dataroots": {"library": {"acme_pdk": {"acme_pdk": "opt/pdks/acme"}}}},
     "each path absolute"),
    ({"private_dataroots": {"tool": {"acme_sim": "/opt/acme"}}}, "each path absolute"),
    ({"private_dataroots": {"task": {"acme_sim": {"scripts": "/opt/acme"}}}},
     "each path absolute"),
])
def test_a_config_that_would_mean_something_else_is_refused(values, complaint):
    from siliconcompiler.remote.server.config import Config

    with pytest.raises(ValueError, match=complaint):
        Config.load(write_config(values))


@pytest.mark.parametrize("limit", ["pending_uploads", "concurrent_jobs", "max_download_bytes"])
def test_a_null_limit_is_unlimited_where_the_server_treats_it_so(limit):
    assert create_app(write_config({"limits": {limit: None}})) \
        .config["SC_CONFIG"].limits[limit] is None


def test_every_private_root_is_given_to_jobs_once():
    from siliconcompiler.remote.server.config import Config, private_paths

    datadir = write_config({"private_dataroots": {
        "library": {"acme_pdk": {"acme_pdk": "/opt/pdks/acme"}},
        "tool": {"acme_sim": {"scripts": "/opt/acme"}},
        "task": {"acme_sim": {"check": {"scripts": "/opt/acme-check"},
                              "run": {"scripts": "/opt/acme"}}}}})

    assert private_paths(Config.load(datadir)["private_dataroots"]) == [
        "/opt/pdks/acme", "/opt/acme", "/opt/acme-check"]


def test_the_store_survives_a_restart_and_storage_is_a_file_uri_in_it(server, client):
    '''A restart used to lose every running job. A location is a row and
    uri_base a URI, so file:// is a first-class deployment.'''
    first = client.get("/v1").get_json()

    assert create_app("datadir").test_client().get("/v1").get_json() == first
    assert Path("datadir/server.db").exists()

    location = server.config["SC_STORE"].one("SELECT * FROM storage_locations")

    assert location["id"] == "primary"
    assert location["uri_base"].startswith("file:///")
    assert location["uri_base"].endswith("/artifacts/")
    assert location["writable"] == 1


def test_the_registry_is_the_contracts_thirty_eight():
    '''Frozen at v1 in SiliconCompiler's namespace, not a deployment's, so a
    client branches across implementations. No slug outside it can be raised,
    and four are only ever a job's or node's error `type`.'''
    assert TYPE_BASE == "https://siliconcompiler.com/server-errors"
    assert len(ERRORS) == 38
    assert {"software-unavailable", "resource-unavailable", "upload-forbidden"} <= set(ERRORS)
    assert all(err.uri == f"{TYPE_BASE}/{slug}" for slug, err in ERRORS.items())

    assert {slug for slug, err in ERRORS.items() if err.status is None} == {
        "run-interrupted", "run-failed", "staging-failed", "staging-timed-out"}
    with pytest.raises(ValueError, match="never an HTTP response"):
        ProblemError("run-failed")
    with pytest.raises(KeyError):
        ProblemError("made-up-condition")


def test_the_discriminator_is_a_member_not_the_slug():
    '''A member's value can be added after the freeze; a slug cannot.'''
    body = problem("limit-exceeded", detail="four already running", limit="concurrent_jobs")

    assert body["type"] == f"{TYPE_BASE}/limit-exceeded"
    assert body["limit"] == "concurrent_jobs"
    assert body["status"] == 429


def test_routing_refusals_are_problem_json(client):
    '''RFC 9110 requires `Allow` on a 405.'''
    unrouted = client.get("/v1/nothing-here")
    wrong = client.post("/v1")

    assert (unrouted.status_code, wrong.status_code) == (404, 405)
    for resp in (unrouted, wrong):
        assert resp.mimetype == "application/problem+json"
    assert unrouted.get_json()["type"] == f"{TYPE_BASE}/not-found"
    assert wrong.get_json()["type"] == f"{TYPE_BASE}/method-not-allowed"
    assert "GET" in wrong.headers["Allow"]


def test_a_raised_problem_renders_with_its_members(server):
    '''Raised where it is decided, rendered at the edge.'''
    @server.route("/v1/_boom")
    def boom():
        raise ProblemError("feature-unsupported",
                           detail="this deployment does not do device grants",
                           feature="device_grant")

    resp = server.test_client().get("/v1/_boom")

    assert resp.status_code == 501
    assert resp.mimetype == "application/problem+json"
    body = resp.get_json()
    trace_id = body.pop("trace_id")
    assert body == {
        "type": f"{TYPE_BASE}/feature-unsupported",
        "title": "This deployment does not support that",
        "status": 501,
        "detail": "this deployment does not do device grants",
        "feature": "device_grant",
        "instance": "/v1/_boom",
    }
    assert len(trace_id) == 32 and int(trace_id, 16) >= 0


def test_every_refusal_names_its_request(client):
    '''🔴 `instance` and a correlation id on every problem body (surface
    D152); the caller's own `traceparent` is the id where it sent one.'''
    routed = client.get("/v1/no/such/path").get_json()
    assert routed["instance"] == "/v1/no/such/path" and len(routed["trace_id"]) == 32

    traced = client.get("/v1/no/such/path", headers={
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}).get_json()
    assert traced["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"

    # A malformed one is not trusted, and two requests are two ids.
    assert client.get("/v1/no/such/path", headers={"traceparent": "garbage"}) \
        .get_json()["trace_id"] != routed["trace_id"]


def test_help_works_without_the_server_extra(capsys):
    '''The docs build renders the apps reference from exactly this.'''
    from siliconcompiler.remote.server import __main__ as entry

    with pytest.raises(SystemExit) as exit_code:
        entry.main(["--help"])

    assert exit_code.value.code == 0
    assert "-datadir" in capsys.readouterr().out


def test_running_without_the_server_extra_is_a_message_not_a_traceback(capsys, monkeypatch):
    from siliconcompiler.remote.server import app as app_module
    from siliconcompiler.remote.server import __main__ as entry

    monkeypatch.setattr(app_module, "missing_server_dependency", "flask")

    assert entry.main([]) == 1
    err = capsys.readouterr().err
    assert "the server is unavailable" in err
    assert 'pip install "siliconcompiler[server]"' in err


def test_three_flags_and_their_defaults():
    '''Everything else has a default in <datadir>/config.json. ⚠️ The fourth
    is for testing, and off unless asked for.'''
    from siliconcompiler.remote.server import __main__ as entry

    args = entry._parser().parse_args([])

    assert (args.port, args.cluster, args.datadir, args.test_mode) == \
        (8080, "local", "./sc_server", None)
    assert {action.dest for action in entry._parser()._actions} == {
        "help", "port", "datadir", "cluster", "test_mode", "version"}


def test_a_broken_config_is_reported_and_exits_non_zero():
    from siliconcompiler.remote.server import __main__ as entry

    Path("datadir").mkdir()
    Path("datadir/config.json").write_text("{not json")

    assert entry.main(["-datadir", "datadir"]) == 1
