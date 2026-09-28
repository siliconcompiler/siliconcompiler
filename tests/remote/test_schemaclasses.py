import json
import sys

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import outcome, slug                                      # noqa: E402
from test_server_jobs import FakeDispatcher, stage, submit              # noqa: E402


# Contract §1: a manifest a job uploaded is read as data. Every class and task
# module it names is looked up among what this installation provides, and
# nothing is imported on its behalf.


@pytest.fixture
def unloaded(tmp_path, monkeypatch):
    '''A module on the path that nothing has imported, and that says so if it is.'''
    marker = tmp_path / "imported"
    (tmp_path / "sc_uploaded_names.py").write_text(
        f"open({str(marker)!r}, 'w').write('imported')\n"
        "from siliconcompiler.schema import BaseSchema\n"
        "from siliconcompiler.tools.builtin.nop import NOPTask\n"
        "class Named(BaseSchema):\n    pass\n"
        "class NamedTask(NOPTask):\n    pass\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    return marker


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def submitted(server_client, key, token, archive):
    path, digest, size = archive
    job = stage(server_client, key, token, path, size)
    return outcome(server_client, key, token,
                   submit(server_client, key, token, job["id"], digest, size))


def test_a_task_class_this_server_does_not_have_is_refused_and_never_imported(
        server_client, key, token, job_archive, nop_project, dispatcher, unloaded):
    '''🔴 A task's own setup runs on the node, so it is not run as its base
    class instead (surface D163) -- and the module is looked up, not imported.'''
    nop_project.get_flow().get_graph_node("stepone", "0").set(
        "taskmodule", "sc_uploaded_names/NamedTask")

    response = submitted(server_client, key, token, job_archive(nop_project))

    assert response.status_code == 422
    body = response.get_json()
    assert (slug(response), body["reason"]) == ("software-unavailable", "unknown_class")
    assert body["unresolved"] == [
        {"name": "sc_uploaded_names/NamedTask", "requirement": [], "available": []}]
    assert "stepone/0" in body["detail"]
    assert not unloaded.exists()
    assert not dispatcher.submitted


def test_any_other_class_it_names_resolves_to_its_base_unimported(
        server_client, key, token, job_archive, nop_project, dispatcher, unloaded):
    original = nop_project.write_manifest

    def write(path, *args, **kwargs):
        original(path, *args, **kwargs)
        with open(path) as f:
            manifest = json.load(f)
        manifest["__meta__"]["class"] = "sc_uploaded_names/Named"
        with open(path, "w") as f:
            json.dump(manifest, f)

    nop_project.write_manifest = write

    response = submitted(server_client, key, token, job_archive(nop_project))

    assert response.status_code == 202, response.get_json()
    assert not unloaded.exists()


def test_nothing_under_the_data_directory_is_importable(tmp_path):
    from siliconcompiler.remote.server.app import create_app

    datadir = tmp_path / "datadir"
    sys.path.insert(0, str(datadir / "users"))
    try:
        create_app(str(datadir), cluster="local")
        assert not [entry for entry in sys.path if entry.startswith(str(datadir))]
    finally:
        sys.path[:] = [entry for entry in sys.path if not entry.startswith(str(datadir))]


def test_a_python_source_is_answered_without_importing_its_parent(tmp_path, monkeypatch):
    '''`find_spec` on a dotted name imports the parent first.'''
    from siliconcompiler.remote.server.jobs import _Supply

    marker = tmp_path / "imported"
    package = tmp_path / "sc_uploaded_pkg"
    package.mkdir()
    (package / "__init__.py").write_text(f"open({str(marker)!r}, 'w').write('x')\n")
    (package / "sub.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))

    supply = _Supply({"private_dataroots": {}}, None)

    assert supply.package("sc_uploaded_pkg")            # top level: found, not run
    assert not supply.package("sc_uploaded_pkg.sub")    # parent not loaded here
    assert not supply.package("not an identifier")
    assert not marker.exists()


###########################
# A job nobody is at (surface D165)
###########################

def _with_node(project, task, name):
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask

    flow = Flowgraph(name)
    flow.node("stepone", NOPTask())
    flow.node("look", task)
    flow.edge("stepone", "look")
    project.set_flow(flow)
    return project


def test_a_breakpoint_is_refused_naming_the_node(
        server_client, key, token, job_archive, nop_project, dispatcher):
    nop_project.option.set_breakpoint(True, step="steptwo", index="0")

    response = submitted(server_client, key, token, job_archive(nop_project))

    assert response.status_code == 422
    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "breakpoint")
    assert "steptwo/0" in response.get_json()["detail"]
    assert not dispatcher.submitted


def test_a_task_that_opens_a_window_is_refused_and_a_screenshot_is_not(
        server_client, key, token, job_archive, nop_project, dispatcher):
    from siliconcompiler.tools.klayout.screenshot import ScreenshotTask
    from siliconcompiler.tools.klayout.show import ShowTask

    shown = submitted(server_client, key, token,
                      job_archive(_with_node(nop_project, ShowTask(), "shown")))

    assert shown.status_code == 422
    assert shown.get_json()["reason"] == "interactive_task"
    assert "look/0" in shown.get_json()["detail"]

    headless = submitted(server_client, key, token,
                         job_archive(_with_node(nop_project, ScreenshotTask(), "headless")))
    assert headless.status_code == 202, headless.get_json()


def test_the_runner_fails_a_node_whose_task_class_is_not_installed(nop_project):
    '''🔴 Never run as its base class, which would skip the task's own setup:
    the node fails, named, and nothing starts.'''
    from siliconcompiler.remote.server import runner

    nop_project.get_flow().get_graph_node("steptwo", "0").set(
        "taskmodule", "sc_not_installed_anywhere/Task")
    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "pending"},
                                  "steptwo/0": {"state": "pending"}}}

    with pytest.raises(RuntimeError, match="steptwo/0 runs sc_not_installed_anywhere/Task"):
        runner._check_task_classes(nop_project)

    assert runner._progress["nodes"]["steptwo/0"]["state"] == "failed"
    assert runner._progress["nodes"]["stepone/0"]["state"] == "pending"
