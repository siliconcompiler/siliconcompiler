import gzip
import hashlib
import io
import tarfile
import time

from urllib.parse import urlsplit

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.outputs import confine  # noqa: E402

from conftest import finish, slug, write_progress  # noqa: E402


@pytest.fixture
def outside():
    '''A file and a directory beside the build tree, which no job's link may reach.'''
    import os

    os.makedirs("elsewhere")
    with open("secret.txt", "w") as f:
        f.write("not a result")
    return os.path.abspath("secret.txt"), os.path.abspath("elsewhere")


def listed(api, job, query=""):
    return api("GET", f"/v1/jobs/{job['id']}/artifacts{query}").get_json()["items"]


def fetch(server_client, api, job, artifact):
    '''The artifact's bytes, through the 303 and the signed route it names.'''
    redirect = api("GET", f"/v1/jobs/{job['id']}/artifacts/{artifact['id']}")
    assert redirect.status_code == 303
    target = urlsplit(redirect.headers["Location"])
    return server_client.get(f"{target.path}?{target.query}")


def test_a_finished_run_lists_what_the_client_rebuilds_its_directory_from(
        server, api, dispatcher, tree):
    job, root = tree
    assert listed(api, job) == []

    finish(server, api, dispatcher, job)
    items = listed(api, job)

    assert {(a["kind"], a["step"], a["index"]) for a in items} == {
        ("manifest", None, None), ("logs", None, None),
        *((kind, step, "0") for step in ("stepone", "steptwo")
          for kind in ("manifest", "logs", "node"))}
    assert len(items) == 8
    assert {(a["media_type"], a["fetchable"], a["deleted_at"]) for a in items} == \
        {("application/gzip", True, None)}


def test_the_bytes_match_the_listing_and_hold_the_run(server, server_client, api, dispatcher,
                                                      tree):
    job, root = tree
    finish(server, api, dispatcher, job)
    by_kind = {(a["kind"], a["step"]): a for a in listed(api, job)}

    for artifact in by_kind.values():
        body = fetch(server_client, api, job, artifact)
        assert body.status_code == 200
        assert body.headers["X-Content-Type-Options"] == "nosniff"
        assert len(body.data) == artifact["size_bytes"]
        assert artifact["digest"] == f"sha256:{hashlib.sha256(body.data).hexdigest()}"

    flow = fetch(server_client, api, job, by_kind["logs", None]).data
    assert gzip.decompress(flow) == b"the flow\n"
    with tarfile.open(fileobj=io.BytesIO(fetch(server_client, api, job,
                                               by_kind["node", "stepone"]).data)) as tar:
        assert {"sc_stepone_0.log", "outputs/gcd.pkg.json"} <= set(tar.getnames())


@pytest.mark.parametrize("query, expected", [
    ("?kind=node", 2),
    ("?kind=node&kind=logs", 4 + 1),
    ("?step=stepone", 3),
    ("?step=stepone&index=0&kind=logs", 1),
    ("?step=nowhere", 0),
])
def test_the_listing_is_filtered(server, api, dispatcher, tree, query, expected):
    finish(server, api, dispatcher, tree[0])
    assert len(listed(api, tree[0], query)) == expected


def test_the_listing_is_paged_as_the_client_follows(server, api, dispatcher, tree):
    finish(server, api, dispatcher, tree[0])
    job = tree[0]

    page = api("GET", f"/v1/jobs/{job['id']}/artifacts?limit=4&kind=manifest&kind=logs&kind=node")
    assert len(page.get_json()["items"]) == 4
    link = page.headers["Link"]
    assert 'rel="next"' in link and "kind=manifest" in link

    rest = api("GET", link[1:link.index(">")])
    assert len(rest.get_json()["items"]) == 4 and "Link" not in rest.headers
    assert not {a["id"] for a in page.get_json()["items"]} & \
        {a["id"] for a in rest.get_json()["items"]}


def test_a_bad_cursor_is_named(api, tree):
    refused = api("GET", f"/v1/jobs/{tree[0]['id']}/artifacts?cursor=zz")
    assert (refused.status_code, slug(refused)) == (400, "invalid-cursor")


def test_a_node_is_kept_when_it_finishes_and_the_job_once_it_does(
        server, api, dispatcher, tree):
    job, _ = tree
    write_progress(server, job, "running", {"stepone/0": "completed", "steptwo/0": "running"})
    # Kept on a thread: the node reads terminal once they are listed.
    while not api("GET", f"/v1/jobs/{job['id']}").get_json()["nodes"][0]["terminal"]:
        time.sleep(0.05)
    first = listed(api, job)
    assert {(a["kind"], a["step"]) for a in first} == {("manifest", "stepone"),
                                                       ("logs", "stepone"),
                                                       ("node", "stepone")}

    finish(server, api, dispatcher, job)
    after = listed(api, job)
    assert len(after) == 8 and {a["id"] for a in first} < {a["id"] for a in after}
    assert {a["id"] for a in after} == {a["id"] for a in listed(api, job)}


def test_a_link_out_of_the_tree_is_never_followed(server, server_client, api, dispatcher, tree,
                                                  outside):
    secret, elsewhere = outside
    job, root = tree
    one, two = root / "stepone" / "0", root / "steptwo" / "0"
    (one / "leak").symlink_to(secret)
    (one / "escape").symlink_to(elsewhere)
    (one / "inside").symlink_to("sc_stepone_0.log")
    (one / "outputs" / "gcd.pkg.json").unlink()
    (one / "outputs" / "gcd.pkg.json").symlink_to(secret)
    (two / "sc_steptwo_0.log").unlink()
    (two / "sc_steptwo_0.log").symlink_to(secret)
    (root / "job.log").unlink()
    (root / "job.log").symlink_to(secret)

    finish(server, api, dispatcher, job)
    items = listed(api, job)
    kept = {(a["kind"], a["step"]) for a in items}

    assert {("logs", None), ("logs", "steptwo"), ("manifest", "stepone")}.isdisjoint(kept)
    node, = [a for a in items if (a["kind"], a["step"]) == ("node", "stepone")]
    with tarfile.open(fileobj=io.BytesIO(fetch(server_client, api, job, node).data)) as tar:
        members = {m.name: m for m in tar.getmembers()}
    assert "leak" not in members and "escape" not in members
    assert members["inside"].issym() and members["inside"].linkname == "sc_stepone_0.log"
    assert "outputs/gcd.pkg.json" not in members


def test_confine_refuses_a_link_in_the_path_and_a_fifo(outside):
    import os

    secret, elsewhere = outside
    os.makedirs("tree/dir")
    os.symlink(elsewhere, "tree/linked")
    open(os.path.join(elsewhere, "inner"), "w").close()
    os.mkfifo("tree/pipe")
    os.symlink(secret, "tree/dir/file")

    for path in ("tree/linked/inner", "tree/dir/file", "tree/pipe", "tree/../secret.txt"):
        with pytest.raises(OSError):
            confine.open_inside("tree", path)


def test_a_stranger_finds_nothing(server_client, server, api, stranger, dispatcher, tree):
    job, _ = tree
    finish(server, api, dispatcher, job)
    artifact = listed(api, job)[0]

    for path in (f"/v1/jobs/{job['id']}/artifacts",
                 f"/v1/jobs/{job['id']}/artifacts/{artifact['id']}"):
        refused = stranger("GET", path)
        assert (refused.status_code, slug(refused)) == (404, "not-found")

    missing = api("GET", f"/v1/jobs/{job['id']}/artifacts/no-such-artifact")
    assert (missing.status_code, slug(missing)) == (404, "not-found")


def test_a_deleted_job_keeps_no_artifacts(server, api, dispatcher, tree):
    job, _ = tree
    finish(server, api, dispatcher, job)
    artifact = listed(api, job)[0]
    assert api("DELETE", f"/v1/jobs/{job['id']}").status_code == 204

    for path in ("artifacts", f"artifacts/{artifact['id']}"):
        assert api("GET", f"/v1/jobs/{job['id']}/{path}").status_code == 404
    assert not server.config["SC_JOBS"].storage.artifact_dir(job["id"]).exists()


@pytest.mark.parametrize("damage", ["signature", "expiry", "job"])
def test_a_signed_download_url_binds_its_object_and_expires(
        server_client, server, api, dispatcher, tree, damage):
    job, _ = tree
    finish(server, api, dispatcher, job)
    artifact = listed(api, job)[0]
    target = urlsplit(api("GET", f"/v1/jobs/{job['id']}/artifacts/{artifact['id']}")
                      .headers["Location"])
    path, query = target.path, target.query
    if damage == "signature":
        query = query[:-3] + "AAA"
    elif damage == "expiry":
        query = query.replace("expires=", "expires=1")
    else:
        path = path.replace(job["id"], "0" * 8)

    refused = server_client.get(f"{path}?{query}")

    assert (refused.status_code, slug(refused)) == (400, "invalid-request")
