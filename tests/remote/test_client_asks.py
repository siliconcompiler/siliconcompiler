import json
import os
import threading

import pytest
import responses

from siliconcompiler import Design, Flowgraph, PDK, Project
from siliconcompiler.remote import Client, Credentials, RemoteError
from siliconcompiler.remote.client.run import RemoteRun, _CannotSupply, _scrubbed

from test_capture import _distribution, site  # noqa: F401


pytest.importorskip("flask", reason="the server extra is not installed")


# 🔴 A client that cannot supply what the server asks for cancels the job,
# naming each item and why (surface D287) -- at create, after submit, and for
# a Python package alike, and never with a partial answer.

# Nothing listens here, and its credentials would be in any message that
# echoed the URL.
UNREACHABLE = "https://someone:hunter2@127.0.0.1:9/acme/pdk/archive/"


@pytest.fixture
def rig(request):
    '''A server on an ephemeral port with the parameter as its `config.json`,
    and a client for it: ``(url, app, client)``.'''
    from werkzeug.serving import make_server

    from siliconcompiler.remote.server.app import create_app

    os.makedirs("datadir", exist_ok=True)
    with open("datadir/config.json", "w") as f:
        json.dump(getattr(request, "param", {}), f)

    app = create_app(os.path.abspath("datadir"), cluster="local")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    url = f"http://127.0.0.1:{server.server_port}"
    app.config["SC_PUBLIC_ORIGINS"] = [url]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    credentials = Credentials(os.path.abspath("sc-home/auth/remote.json"))
    credentials.set_server(url)
    try:
        yield url, app, Client(credentials)
    finally:
        server.shutdown()
        thread.join(timeout=10)


def acme(tag):
    pdk = PDK("acme")
    pdk.set_dataroot("acme", UNREACHABLE, tag=tag)
    with pdk.active_dataroot("acme"):
        pdk.set("package", "doc", "datasheet", "notes.txt")
    return pdk


def the_job(app, client):
    '''The one job this client ran, as the wire shows it and as the store
    keeps it -- the same reason, served whole (surface D288).'''
    job, = client.jobs()
    row = dict(app.config["SC_STORE"].one(
        "SELECT state, state_reason FROM jobs WHERE id = ?", (job["id"],)))
    detail, _ = client.job(job["id"])
    assert detail["state"] == "cancelled" == row["state"]
    assert detail["transitions"][-1]["reason"] == row["state_reason"]
    assert "hunter2" not in row["state_reason"]
    return detail, row


@pytest.mark.parametrize("rig,when", [
    ({}, "create"),
    # Allowlisted, so not asked for at create; the server's fetch fails, and
    # the job comes back asking.
    ({"fetch_fails": True, "fetch_allowlist": ["https://127.0.0.1:9/acme/"]}, "after"),
], indirect=["rig"], ids=["at-create", "after-submit"])
def test_a_source_asked_for_that_cannot_be_fetched_here_cancels(rig, nop_project, when):
    url, app, client = rig
    nop_project.add_dep(acme(f"v1-{when}"))
    # The first node reads its datasheet, so the create names it.
    nop_project.add("tool", "builtin", "task", "nop", "require",
                    "library,acme,package,doc,datasheet", step="stepone", index="0")

    with pytest.raises(RemoteError, match=r"the dataroot library,acme,dataroot,acme: it "
                                          r"cannot be fetched here"):
        RemoteRun(nop_project, client).run()

    detail, row = the_job(app, client)
    if when == "create":
        assert row["state_reason"].startswith(
            "cancelled from sc-remote: it cannot supply what the server asked for: "
            "the dataroot library,acme,dataroot,acme")
        # Nothing moved: no upload was ever granted.
        assert app.config["SC_STORE"].one("SELECT count(*) AS n FROM artifacts")["n"] == 0
    else:
        assert [entry["state"] for entry in detail["transitions"]][-3:] == \
            ["staging", "awaiting_input", "cancelled"]
        assert "library,acme,dataroot,acme" in row["state_reason"]


def cocotb_project(test_body):
    from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask

    os.makedirs("bench", exist_ok=True)
    open("bench/test_gcd.py", "w").write(test_body)
    design = Design("gcd")
    design.set_dataroot("bench", os.path.abspath("bench"))
    with design.active_dataroot("bench"), design.active_fileset("tb"):
        design.set_topmodule("gcd")
        design.add_file("test_gcd.py", filetype="python")
    project = Project(design)
    project.add_fileset("tb")
    flow = Flowgraph("cocotbflow")
    flow.node("sim", CocotbExecTask())
    project.set_flow(flow)
    project.option.set_nodashboard(True)
    project.option.set_jobname("job0")
    project.option.set_builddir(os.path.abspath("build"))
    return project


@pytest.mark.parametrize("rig", [{"features": ["logs.stream", "logs.stream.job",
                                               "python.env"]}], indirect=True)
def test_a_compiled_package_asked_for_cancels_naming_its_file(rig, site, monkeypatch):  # noqa: F811
    '''No configured index has it, so the server asks for its wheel, and a
    compiled file cannot be sent.'''
    from siliconcompiler.remote.server.packages import envinstall

    def absent(packages, wheels, root, logger, constrain=(), indexes=(), **_):
        raise envinstall.InstallFailed({"returncode": 1, "absent": ["scfakec"]})

    monkeypatch.setattr(envinstall, "install", absent)
    _distribution(site, "scfakec", "1.0.0", files={"_c.so": "\x7fELF"})
    # What a cocotb task's `requested_versions.python` names, held by the
    # server's own Python as by this one.
    _distribution(site, "cocotb", "2.1.0")
    url, app, client = rig

    with pytest.raises(RemoteError, match="scfakec: it holds a compiled file"):
        RemoteRun(cocotb_project("import scfakec\n"), client).run()

    _, row = the_job(app, client)
    assert "the Python package scfakec: it holds a compiled file, scfakec/_c.so" in \
        row["state_reason"]


def _cancel_reason(fake_v1):
    cancel, = [c for c in fake_v1.calls if c.request.path_url.endswith("/cancel")]
    return json.loads(cancel.request.body)["reason"]


@pytest.fixture
def cancels(fake_v1):
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                  {"id": "01J9-job", "state": "cancelled", "terminal": True}, status=202)


def test_one_item_that_cannot_be_had_sends_none_and_names_every_failure(
        site, fake_v1, cancels, logged_in, nop_project, monkeypatch):  # noqa: F811
    '''🔴 Every item is tried before anything is collected: one that cannot be
    had cancels the job, naming each, and nothing is uploaded.'''
    from siliconcompiler.package.https import HTTPResolver

    def unreachable(self):
        raise FileNotFoundError("connection refused by https://someone:hunter2@127.0.0.1:9/")

    _distribution(site, "scfakec", "1.0.0", files={"_c.so": "x"})
    _distribution(site, "scfakefine", "2.0.0")
    nop_project.add_dep(acme("v1-partial"))
    monkeypatch.setattr(HTTPResolver, "resolve_remote", unreachable)

    with pytest.raises(RemoteError) as raised:
        RemoteRun(nop_project, logged_in)._send_asked("01J9-job", [
            {"kind": "dataroot", "keypath": ["library", "acme", "dataroot", "acme"]},
            {"kind": "python", "name": "scfakefine"},
            {"kind": "python", "name": "scfakec"},
            {"kind": "python", "name": "scfakegone"}])

    assert not [c for c in fake_v1.calls if "upload-grant" in c.request.path_url]
    reason = _cancel_reason(fake_v1)
    failed = ("the dataroot library,acme,dataroot,acme: it cannot be fetched here either",
              "the Python package scfakec: it holds a compiled file",
              "the Python package scfakegone: it is not installed here either")
    # Every one printed here; in the reason, those that fit and how many more.
    assert all(one in str(raised.value) for one in failed)
    named = sum(one in reason for one in failed)
    assert named and (named == 3 or reason.endswith(f"; and {3 - named} more"))
    assert len(reason) <= 300
    assert "scfakefine" not in reason
    assert "hunter2" not in reason and "hunter2" not in str(raised.value)


def test_a_long_reason_is_fitted_to_what_the_server_takes(fake_v1, cancels, logged_in,
                                                          nop_project):
    '''🔴 The items that fit, then *and N more* (surface D288), on one line
    within 300; an item too long even alone is cut, so something is named.'''
    run = RemoteRun(nop_project, logged_in)
    failures = [f"lib{n} (lib{n}): it cannot be fetched here either:\n404" for n in range(20)]

    run._abandon("01J9-job", _CannotSupply(failures))

    reason = _cancel_reason(fake_v1)
    assert len(reason) <= 300 and "\n" not in reason
    assert reason.startswith("cancelled from sc-remote: it cannot supply what the server "
                             "asked for: lib0 (lib0)")
    named = reason.count("it cannot be fetched here either")
    assert 0 < named < 20
    assert reason.endswith(f"; and {20 - named} more")

    fake_v1.calls.reset()
    run._abandon("01J9-job", _CannotSupply(["x" * 2000]))
    assert len(_cancel_reason(fake_v1)) <= 300


def test_no_credential_survives_in_what_is_said():
    assert _scrubbed("git clone https://user:tok@host/x.git failed; ssh://git:pw@h/y") == \
        "git clone https://host/x.git failed; ssh://h/y"
