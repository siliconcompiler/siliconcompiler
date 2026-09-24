import json

import pytest
import requests
import responses


# The conformance rig has no server behind it, so it is worth proving that it
# answers at all before any client is written against it. These go away once
# real client tests exercise the same fixtures.


def test_capabilities_are_served(fake_v1, capabilities):
    '''GET /v1 is answered from the fixture file, with nothing listening.'''
    resp = requests.get(fake_v1.url())

    assert resp.status_code == 200
    assert resp.json() == capabilities
    assert len(fake_v1.calls) == 1


def test_capabilities_carry_every_required_member(capabilities):
    '''Every member of the block is real, which is what phase 1 owes.

    `software` renders from software_versions and is empty until the image
    registry lands, but the key is required to exist, and `siliconcompiler` is
    required to be in it.
    '''
    required = {"api_version", "software", "grant_types_supported", "limits",
                "features", "identity_assurance", "notices"}
    assert required <= set(capabilities)

    assert capabilities["api_version"] == "v1"
    # 🔴 Two buckets, a closed set, both always present -- a client branches
    # on them. `siliconcompiler` is REQUIRED and it lives in `python`, because
    # the bucket a name is published under is part of what the key means.
    assert set(capabilities["software"]) == {"python", "tools"}
    assert "siliconcompiler" in capabilities["software"]["python"]

    # The device grant is not served by this profile, so it must not be
    # advertised: grant_types_supported is what the client branches on.
    assert "urn:ietf:params:oauth:grant-type:device_code" \
        not in capabilities["grant_types_supported"]

    # Every one of them a base unit named by its own key, and the same set the
    # server publishes -- this fixture file is the conformance rig's copy of a
    # real GET /v1, so the two drifting is the defect it exists to catch.
    assert set(capabilities["limits"]) == {
        "max_job_nodes", "max_upload_bytes", "job_retention_days",
        "pending_uploads", "concurrent_jobs", "concurrent_log_streams",
        "max_log_stream_seconds", "max_archive_members",
        "max_archive_expanded_bytes",
        # The nine above are the contract's; these two are this profile's,
        # and `run_heartbeat_seconds` is deliberately NOT among them -- no
        # client sends a heartbeat or is told about one, so publishing its
        # period would be a promise about machinery on the far side of the
        # API. It is deployment config.
        "max_download_bytes",
        "abandon_after_seconds"}

    # terms_url is OPTIONAL and absent unless an operator sets one, which is
    # this deployment's default. Absent is not the same as empty.
    assert "terms_url" not in capabilities


def test_a_test_can_override_a_route(fake_v1):
    '''The last registration wins, so any answer can be provoked.

    This is the whole reason the rig exists: a working server cannot be made to
    return a given refusal on demand.
    '''
    fake_v1.route(responses.GET, "", {"detail": "nope"}, status=503,
                  content_type="application/problem+json")

    assert requests.get(fake_v1.url()).status_code == 200      # the first registration
    assert requests.get(fake_v1.url()).status_code == 503      # then the override


def test_url_keeps_the_version_prefix(fake_v1):
    '''A path is joined onto the base, never urljoin()'d.

    urljoin("https://host/v1", "jobs") is "https://host/jobs" -- the version
    prefix is dropped. The client rewrite has one request path and this is the
    bug it walks into on day one if nobody knows.
    '''
    assert fake_v1.url("jobs") == "https://sc-server.test/v1/jobs"
    assert fake_v1.url("/jobs") == "https://sc-server.test/v1/jobs"
    assert fake_v1.url() == "https://sc-server.test/v1"


def test_non_json_body_is_served_as_given(fake_v1):
    '''A proxy's HTML 502 is a legal answer and the client must tolerate it.

    problem+json is promised only for what a handler produced, so resp.json()
    throws on exactly the errors production serves most.
    '''
    fake_v1.route(responses.GET, "jobs", "<html><body>502</body></html>",
                  status=502, content_type="text/html")

    resp = requests.get(fake_v1.url("jobs"))

    assert resp.status_code == 502
    with pytest.raises(json.JSONDecodeError):
        resp.json()
