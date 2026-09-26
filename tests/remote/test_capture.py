import json
import os
import tarfile

import pytest

from siliconcompiler import Flowgraph, Project
from siliconcompiler.remote import environment
from siliconcompiler.remote.client import capture
from siliconcompiler.tool import PythonEnvironment
from siliconcompiler.tools.builtin.nop import NOPTask


# A node's own Python, read off the submitting machine and written as its
# environment file (surface D131): pinned where it came from an index, sent as
# the user's own code where no index can reproduce it, and never what the
# image holds.


def _distribution(site, name, version, requires=(), editable_source=None):
    '''An installed distribution in ``site``, as pip would leave it -- or,
    with ``editable_source``, one installed editable from there.'''
    dist_info = os.path.join(site, f"{name}-{version}.dist-info")
    os.makedirs(dist_info)
    with open(os.path.join(dist_info, "METADATA"), "w") as f:
        f.write(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        for requirement in requires:
            f.write(f"Requires-Dist: {requirement}\n")
    with open(os.path.join(dist_info, "top_level.txt"), "w") as f:
        f.write(f"{name}\n")

    root = editable_source or site
    os.makedirs(os.path.join(root, name))
    with open(os.path.join(root, name, "__init__.py"), "w") as f:
        f.write("VALUE = 1\n")
    if editable_source:
        with open(os.path.join(dist_info, "direct_url.json"), "w") as f:
            json.dump({"url": f"file://{editable_source}", "dir_info": {"editable": True}}, f)
    return dist_info


@pytest.fixture
def site(monkeypatch):
    site = os.path.abspath("site")
    os.makedirs(site)
    monkeypatch.syspath_prepend(site)
    capture._module_distributions.cache_clear()
    yield site
    capture._module_distributions.cache_clear()


def test_what_a_source_imports():
    with open("tb.py", "w") as f:
        f.write("import os\nimport scfakeumi.sub\nfrom cocotb.triggers import Timer\n"
                "from . import sibling\nimport numpy as np, json\n")
    with open("broken.py", "w") as f:
        f.write("not python(\n")

    assert capture.imported_modules(["tb.py", "broken.py", "missing.py"]) == \
        {"scfakeumi", "cocotb", "numpy"}


def test_what_came_from_an_index_is_pinned_with_what_it_pulls_in(site):
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits>=1"])
    _distribution(site, "scfakebits", "1.2.0")

    found = capture.capture({"scfakeumi"}, [], provided=[])

    assert found.pins == [("scfakebits", "1.2.0"), ("scfakeumi", "0.3.1")]
    assert found.forwarded == [] and found.warnings == []


def test_an_editable_install_is_sent_as_code_not_pinned(site, monkeypatch):
    source = os.path.abspath("checkout")
    dist_info = _distribution(site, "scfakeumi", "0.3.1", editable_source=source)
    monkeypatch.syspath_prepend(source)          # what the editable hook does

    found = capture.capture({"scfakeumi"}, [], provided=[])

    assert found.pins == []
    (pin, paths), = found.forwarded
    assert pin == "scfakeumi==0.3.1"
    assert os.path.join(source, "scfakeumi") in paths and dist_info in paths


def test_what_the_image_holds_is_left_out(site):
    '''🔴 SiliconCompiler and what `requires.python` pins come with the image:
    a second copy on the tool's path is two versions of one package.'''
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0")

    found = capture.capture({"scfakeumi"}, [], provided=["scfakeumi"])

    assert found.pins == []


def test_a_requirement_by_name_follows_its_extras(site):
    _distribution(site, "scfakeumi", "0.3.1", requires=['scfakebits ; extra == "bits"'])
    _distribution(site, "scfakebits", "1.2.0")

    assert capture.capture([], ["scfakeumi"], []).pins == [("scfakeumi", "0.3.1")]
    assert capture.capture([], ["scfakeumi[bits]"], []).pins == \
        [("scfakebits", "1.2.0"), ("scfakeumi", "0.3.1")]


def test_a_module_no_distribution_provides_is_left_out(site):
    assert capture.capture({"scnosuchmodule"}, [], []).pins == []


###########################
# The task's half
###########################

class RunsATestbench(NOPTask):
    '''A task whose tool runs a testbench of the user's.'''

    def get_python_environment(self):
        return PythonEnvironment(sources=(os.path.abspath("tb.py"),),
                                 framework=("scfakebits",))


@pytest.fixture
def project(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    flow.node("sim", RunsATestbench())
    project.set_flow(flow)
    project.option.set_nodashboard(True)
    project.option.set_jobname("job0")
    project.option.set_builddir(os.path.abspath("build"))
    return project


def test_a_task_runs_none_of_the_users_python_by_default():
    assert NOPTask().get_python_environment() is None


def test_forwarded_packages_go_first_on_the_tools_path(project):
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.utils.paths import jobdir

    forwarded = os.path.join(jobdir(project), environment.packages_path("sim", "0"))
    node = SchedulerNode(project, "sim", "0")

    with node.runtime():
        before = node.task.get_runtime_environmental_variables().get("PYTHONPATH", "")
    assert forwarded not in before.split(os.pathsep)      # nothing sent, nothing added

    os.makedirs(forwarded)
    with node.runtime():
        path = node.task.get_runtime_environmental_variables()["PYTHONPATH"]
    assert path.split(os.pathsep)[0] == forwarded


def test_a_cocotb_node_names_its_testbench_and_leaves_cocotb_to_the_image():
    '''cocotb is SiliconCompiler's for a cocotb task: this process sets the
    GPI up from its own copy, so the image holds it and the testbench's file
    leaves it out.'''
    from siliconcompiler import Design
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask

    with open("test_gcd.py", "w") as f:
        f.write("import cocotb\n")
    design = Design("gcd")
    design.set_dataroot("here", os.getcwd())
    with design.active_dataroot("here"), design.active_fileset("tb"):
        design.set_topmodule("gcd")
        design.add_file("test_gcd.py", filetype="python")

    project = Project(design)
    project.add_fileset("tb")
    flow = Flowgraph("cocotbflow")
    flow.node("sim", CocotbExecTask())
    project.set_flow(flow)

    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        wanted = node.task.get_python_environment()

    assert [os.path.basename(path) for path in wanted.sources] == ["test_gcd.py"]
    assert wanted.framework == ("cocotb",)


###########################
# The client writes it
###########################

def test_the_client_writes_each_nodes_file_and_forwards_beside_it(
        site, project, fake_v1, logged_in, monkeypatch):
    from siliconcompiler.remote.client.run import RemoteRun

    source = os.path.abspath("checkout")
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0")
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)
    monkeypatch.syspath_prepend(source)
    with open("tb.py", "w") as f:
        f.write("import scfakeumi\nimport scfakeedit\n")
    monkeypatch.setenv("PIP_INDEX_URL", "https://user:token@pkgs.example.com/simple/")

    run = RemoteRun(project, logged_in)
    run._collect()
    run._pack(__import__("pathlib").Path("upload.tar.gz"))

    with tarfile.open("upload.tar.gz") as tar:
        names = tar.getnames()
        text = tar.extractfile(environment.path_for("sim", "0")).read().decode()

    parsed = environment.parse(text.encode())
    # The framework's -- scfakebits, as cocotb would be -- is the image's.
    assert [str(pin) for pin in parsed.pins] == ["scfakeumi==0.3.1"]
    # The user's own pip index, with its credential stripped.
    assert parsed.index_url == "https://pkgs.example.com/simple/"
    assert text.startswith("# Generated by SiliconCompiler")
    assert f"{environment.packages_path('sim', '0')}/scfakeedit/__init__.py" in names

    # And the create says so, for the refusal before the upload.
    assert run._python_env_files()
    assert run._requires_python()["scfakebits"] == ["==1.2.0"]


###########################
# The server takes what is beside it
###########################

@pytest.fixture
def builds(server):
    server.config["SC_CONFIG"]._values["features"] = \
        server.config["SC_CONFIG"]["features"] + ["python.env"]
    return server


@pytest.fixture
def dispatcher(server):
    from test_server_jobs import FakeDispatcher

    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def _submitted(server_client, key, token, job_archive, extra):
    from test_server_jobs import stage, submit

    path, digest, size = job_archive(extra=extra)
    job = stage(server_client, key, token, path, size)
    return submit(server_client, key, token, job["id"], digest, size)


def test_forwarded_packages_beside_a_file_are_the_users_code(
        builds, server_client, key, token, job_archive, dispatcher):
    pytest.importorskip("flask")
    response = _submitted(server_client, key, token, job_archive, {
        environment.path_for("stepone", "0"): b"numpy==2.0.1\n",
        f"{environment.packages_path('stepone', '0')}/mine/__init__.py": b"VALUE = 1\n"})

    assert response.status_code == 202, response.get_json()


def test_packages_for_a_node_with_no_file_are_refused(
        builds, server_client, key, token, job_archive, dispatcher):
    pytest.importorskip("flask")
    response = _submitted(server_client, key, token, job_archive, {
        f"{environment.packages_path('stepone', '0')}/mine/__init__.py": b"VALUE = 1\n"})

    assert response.get_json()["violation"] == "environment_file"
