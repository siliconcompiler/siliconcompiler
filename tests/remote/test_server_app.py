import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler import __version__  # noqa: E402
from siliconcompiler.remote.server.errors import ERRORS, problem  # noqa: E402

from conftest import slug  # noqa: E402


def test_the_capabilities_have_the_shape_the_client_reads(server_client, capabilities):
    '''GET /v1 publishes the fixture's members, and this process's own software.'''
    body = server_client.get("/v1").get_json()

    assert set(body) == set(capabilities)
    assert body["limits"] == capabilities["limits"]
    assert body["grant_types_supported"] == capabilities["grant_types_supported"]
    assert body["identity_assurance"] == "self_asserted"
    assert body["software"]["python"] == {"siliconcompiler": [__version__]}
    assert list(body["software"]["interpreter"]) == ["python"]
    assert body["features"] == ["logs.stream"]
    assert body["notices"] == []


def test_the_health_check_passes_with_no_credential(server_client):
    response = server_client.get("/v1/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "pass"}


@pytest.mark.parametrize("method, path, status, expected", [
    ("GET", "/v1/nothing", 404, "not-found"),
    ("PUT", "/v1/healthz", 405, "method-not-allowed"),
])
def test_a_refusal_is_problem_json_with_a_help_link(server_client, method, path, status,
                                                    expected):
    response = server_client.open(path, method=method)

    assert response.status_code == status
    assert response.mimetype == "application/problem+json"
    assert slug(response) == expected
    assert response.headers["Link"] == f'</server-errors/{expected}>; rel="help"'
    assert response.headers["Cache-Control"] == "private, no-store"


def test_a_crash_is_an_untyped_500_that_is_logged(server, server_client, caplog):
    '''A client retries an untyped 5xx, and would not retry what reads as its own invalid
    request.'''
    @server.route("/v1/crash")
    def crash():
        raise RuntimeError("boom")

    response = server_client.get("/v1/crash")

    assert response.status_code == 500
    assert response.mimetype == "application/problem+json"
    assert response.get_json() == {"type": "about:blank", "title": "Internal Server Error",
                                   "status": 500}
    assert "Link" not in response.headers
    assert any(record.exc_info and record.exc_info[0] is RuntimeError
               for record in caplog.records)


def test_a_problem_bounds_its_detail():
    body = problem("invalid-request", detail="a\x00b\n" + "x" * 400)

    assert body["detail"].startswith("ab x") and body["detail"].endswith("...")
    assert len(body["detail"]) == 303


def test_a_problem_that_is_never_a_response_has_no_status():
    assert "status" not in problem("run-failed")


@pytest.mark.parametrize("name", [*ERRORS, "index"])
def test_every_registered_type_has_a_page(server_client, name):
    response = server_client.get(f"/server-errors/{name}")

    assert response.status_code == 200
    assert response.mimetype == "text/html"


def test_the_stylesheet_and_a_missing_page(server_client):
    assert server_client.get("/server-errors/style.css").mimetype == "text/css"
    assert server_client.get("/server-errors/nothing").status_code == 404
    assert server_client.get("/server-errors/_layout").status_code == 404


def test_a_store_survives_a_restart(server_client, key):
    from conftest import login
    from siliconcompiler.remote.server.app import create_app

    user = login(server_client, key).get_json()
    again = create_app("sc-server").config["SC_STORE"]

    assert again.one("SELECT count(*) AS n FROM tokens")["n"] == 2
    assert user["token_type"] == "DPoP"
