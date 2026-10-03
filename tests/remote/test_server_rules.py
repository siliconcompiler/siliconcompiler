import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import call, slug                                         # noqa: E402
from test_server_artifacts import ran                                   # noqa: E402
from test_server_jobs import FakeDispatcher, digest                     # noqa: E402


# The rules the reference schema used to carry, now in the normative files
# (surface D177, entitlements D54, identity D59), each held to here.


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.mark.parametrize("path", ["/v1/jobs?stat=running", "/v1/devices?all=1"])
def test_a_query_parameter_a_collection_does_not_define_is_refused(
        server_client, key, token, path):
    '''Never ignored: a misspelled filter would return everything.'''
    response = call(server_client, key, "GET", path, token)

    assert (response.status_code, slug(response)) == (400, "invalid-request")


def test_the_artifact_listing_refuses_one_too(server, server_client, key, token,
                                              job_archive, dispatcher):
    job = ran(server, server_client, key, token, job_archive)

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job['id']}/artifacts?kinds=logs", token)
    assert (response.status_code, slug(response)) == (400, "invalid-request")

    items = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/artifacts?kind=logs",
                 token).get_json()["items"]
    # REQUIRED on every item, and null here: this profile takes no requests.
    assert items and all(item["access_requested_at"] is None for item in items)


def test_a_device_says_which_is_the_callers(server_client, key, token):
    '''The list and endpoint 11 publish one object, `current` included.'''
    listed, = call(server_client, key, "GET", "/v1/devices", token).get_json()["items"]
    one = call(server_client, key, "GET", f"/v1/devices/{listed['id']}", token).get_json()

    assert listed == one
    assert listed["current"] is True
    assert set(listed) == {"id", "name", "current", "machine_id_source", "enrolled_at",
                           "last_seen_at"}


def test_a_job_delete_never_deletes_what_is_held(server, server_client, key, token,
                                                 job_archive, dispatcher):
    '''🔴 Entitlements D54: the held row and its bytes stay; the rest go.'''
    job = ran(server, server_client, key, token, job_archive)
    store, storage = server.config["SC_STORE"], server.config["SC_STORAGE"]
    held, other = store.all("SELECT id, storage_key FROM artifacts WHERE job_id = ? "
                            "AND step IS NOT NULL ORDER BY id LIMIT 2", (job["id"],))
    store.execute("UPDATE artifacts SET legal_hold_at = '2026-09-01T00:00:00.000Z', "
                  "  legal_hold_by = user_id, legal_hold_reason = 'a case' "
                  "FROM jobs WHERE artifacts.id = ? AND jobs.id = artifacts.job_id",
                  (held["id"],))

    response = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert response.status_code == 204
    kept = store.one("SELECT deleted_at FROM artifacts WHERE id = ?", (held["id"],))
    gone = store.one("SELECT deleted_at FROM artifacts WHERE id = ?", (other["id"],))
    assert kept["deleted_at"] is None and storage.artifact_path(held["storage_key"]).exists()
    assert gone["deleted_at"] is not None
    assert not storage.artifact_path(other["storage_key"]).exists()


def test_a_tool_is_placed_by_preference_and_never_by_the_newest_image():
    '''Where two images hold a tool at different versions, the operator's
    preference chooses -- a reported version before a publish date.'''
    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.software.images import Held, Requirement

    def image(ref, version, preference, built_at, source="reported"):
        return {"id": ref, "registry_ref": ref, "digest": digest("a"), "note": None,
                "built_at": built_at, "resolved_at": None,
                "contents": [Held("siliconcompiler", "0.38.0", 0, "reported", "python"),
                             Held("openroad", version, preference, source, "tool")]}

    older_preferred = image("old", "2.0", 10, "2026-01-01T00:00:00Z")
    newer = image("new", "2.1", 0, "2026-09-01T00:00:00Z")
    undated = image("dated", "20260901", 99, "2026-09-02T00:00:00Z", source="published_date")

    wanted = [Requirement("siliconcompiler", (), "library"), Requirement("openroad", (), "tool")]
    assert images.resolve([newer, older_preferred], wanted)["id"] == "old"
    assert images.resolve([undated, newer], wanted)["id"] == "new"
