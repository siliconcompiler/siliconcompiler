import json
import os
import tarfile

import pytest

from conftest import outcome

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


def bench(*imports, name="tb.py"):
    '''A test module importing ``imports``, and its path.'''
    with open(name, "w") as f:
        f.write("".join(f"import {module}\n" for module in imports))
    return [os.path.abspath(name)]


def test_what_came_from_an_index_is_pinned_with_what_it_pulls_in(site):
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits>=1"])
    _distribution(site, "scfakebits", "1.2.0")

    found = capture.capture(bench("scfakeumi"), [], provided=[])

    assert found.pins == [("scfakebits", "1.2.0"), ("scfakeumi", "0.3.1")]
    assert found.files == {} and found.warnings == []


def test_an_editable_install_is_sent_as_code_not_pinned(site, monkeypatch):
    '''Under its import name, file by file, and never its metadata: the tree
    is laid out as a site-packages directory of modules.'''
    source = os.path.abspath("checkout")
    _distribution(site, "scfakeumi", "0.3.1", editable_source=source)
    monkeypatch.syspath_prepend(source)          # what the editable hook does

    found = capture.capture(bench("scfakeumi"), [], provided=[])

    assert found.pins == []
    assert found.files == {"scfakeumi/__init__.py":
                           os.path.join(source, "scfakeumi", "__init__.py")}


def test_a_package_holding_a_compiled_extension_is_refused_naming_it(site, monkeypatch):
    '''🔴 One built for this machine will not import on the node.'''
    source = os.path.abspath("checkout")
    _distribution(site, "scfakeumi", "0.3.1", editable_source=source)
    open(os.path.join(source, "scfakeumi", "_speedups.cpython-312-x86_64-linux-gnu.so"),
         "wb").write(b"\x7fELF")
    monkeypatch.syspath_prepend(source)

    with pytest.raises(capture.CannotForward, match="scfakeumi 0.3.1.*_speedups"):
        capture.capture(bench("scfakeumi"), [], provided=[])


def test_what_the_image_holds_is_left_out(site):
    '''🔴 SiliconCompiler and what `requires.python` names come with the
    image, with what they depend on: a second copy on the tool's path is two
    versions of one package.'''
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0")

    found = capture.capture(bench("scfakeumi"), [], provided=["scfakeumi"])

    assert found.pins == []


def test_a_requirement_by_name_follows_its_extras(site):
    _distribution(site, "scfakeumi", "0.3.1", requires=['scfakebits ; extra == "bits"'])
    _distribution(site, "scfakebits", "1.2.0")

    assert capture.capture([], ["scfakeumi"], []).pins == [("scfakeumi", "0.3.1")]
    assert capture.capture([], ["scfakeumi[bits]"], []).pins == \
        [("scfakebits", "1.2.0"), ("scfakeumi", "0.3.1")]


def test_a_module_no_distribution_provides_is_left_out_and_said(site):
    found = capture.capture(bench("scnosuchmodule"), [], [])

    assert found.pins == [] and found.files == {}
    assert "scnosuchmodule" in found.warnings[0]


def test_imports_are_followed_through_the_users_helpers(site):
    '''🔴 A test imports a helper beside it, and the helper imports what it
    needs: both are reached. The helpers are the user's own code, sent.'''
    _distribution(site, "scfakeumi", "0.3.1")
    os.makedirs("tests/lib")
    open("tests/checks.py", "w").write("import lib.driver\n")
    open("tests/lib/__init__.py", "w").write("")
    open("tests/lib/driver.py", "w").write("import scfakeumi\n")
    os.makedirs("tests/lib/__pycache__")
    open("tests/lib/__pycache__/driver.cpython-312.pyc", "wb").write(b"\0")
    open("tests/lib/stale.pyc", "wb").write(b"\0")

    found = capture.capture(bench("checks", name="tests/test_top.py"), [], [])

    assert found.pins == [("scfakeumi", "0.3.1")]
    # File by file, and no bytecode.
    assert found.files == {
        "checks.py": os.path.abspath("tests/checks.py"),
        "lib/__init__.py": os.path.abspath("tests/lib/__init__.py"),
        "lib/driver.py": os.path.abspath("tests/lib/driver.py")}


def test_no_link_is_sent(site):
    os.makedirs("tests/lib")
    open("tests/lib/__init__.py", "w").write("")
    open("elsewhere.py", "w").write("SECRET = 1\n")
    os.symlink(os.path.abspath("elsewhere.py"), "tests/lib/linked.py")

    found = capture.capture(bench("lib", name="tests/test_top.py"), [], [])

    assert set(found.files) == {"lib/__init__.py"}
    assert any("linked.py is a link" in warning for warning in found.warnings)


def test_a_helper_holding_a_compiled_extension_is_refused(site):
    os.makedirs("tests/fast")
    open("tests/fast/__init__.py", "w").write("")
    open("tests/fast/_c.so", "wb").write(b"\x7fELF")

    with pytest.raises(capture.CannotForward, match="helper module fast.*_c.so"):
        capture.capture(bench("fast", name="tests/test_top.py"), [], [])


def test_packages_sharing_a_namespace_merge_and_one_path_twice_is_refused():
    '''Built file by file, so a namespace directory two packages share
    merges -- and two sources for one file are refused, rather than one
    overwriting the other.'''
    tree = {}
    capture.place(tree, "acme/a/__init__.py", "/src/one/acme/a/__init__.py", "one")
    capture.place(tree, "acme/b/__init__.py", "/src/two/acme/b/__init__.py", "two")
    capture.place(tree, "acme/a/__init__.py", "/src/one/acme/a/__init__.py", "one")

    assert set(tree) == {"acme/a/__init__.py", "acme/b/__init__.py"}
    with pytest.raises(capture.CannotForward, match="both be sent as acme/a/__init__.py"):
        capture.place(tree, "acme/a/__init__.py", "/src/three/acme/a/__init__.py", "three")


def test_a_test_module_that_cannot_be_read_stops_the_work(site):
    with open("tb.py", "w") as f:
        f.write("not python(\n")

    with pytest.raises(capture.CannotForward, match="cannot be read as Python"):
        capture.capture([os.path.abspath("tb.py")], [], [])


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


def test_the_users_code_goes_first_on_the_path_of_a_node_running_their_python(
        project, gcd_design):
    '''Once per job, and first on the tool's path of every node whose task
    runs the user's Python -- with or without a file of its own -- and never
    on a node whose task runs none.'''
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.utils.paths import jobdir

    forwarded = os.path.join(jobdir(project), environment.packages_path())
    os.makedirs(forwarded)

    def path(project, step):
        node = SchedulerNode(project, step, "0")
        with node.runtime():
            return node.task.get_runtime_environmental_variables().get(
                "PYTHONPATH", "").split(os.pathsep)

    assert path(project, "sim")[0] == forwarded

    plain = Project(gcd_design)
    plain.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    flow.node("sim", NOPTask())
    plain.set_flow(flow)
    plain.option.set_jobname("job0")
    plain.option.set_builddir(os.path.abspath("build"))
    assert forwarded not in path(plain, "sim")


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

def test_the_client_writes_each_nodes_file_and_sends_the_users_code_beside_it(
        site, project, fake_v1, logged_in, monkeypatch):
    '''No index line, and no pip configuration read: every package comes
    from the deployment's own indexes.'''
    from siliconcompiler.remote.client.run import RemoteRun

    source = os.path.abspath("checkout")
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0")
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)
    monkeypatch.syspath_prepend(source)
    with open("tb.py", "w") as f:
        f.write("import scfakeumi\nimport scfakeedit\n")
    monkeypatch.setenv("PIP_INDEX_URL", "https://user:token@pkgs.example.com/simple/")
    monkeypatch.setenv("PIP_EXTRA_INDEX_URL", "https://more.example.com/simple/")

    run = RemoteRun(project, logged_in)
    run._collect()
    run._pack(__import__("pathlib").Path("upload.tar.gz"))

    with tarfile.open("upload.tar.gz") as tar:
        names = tar.getnames()
        text = tar.extractfile(environment.path_for("sim", "0")).read().decode()
        members = [member for member in tar.getmembers()
                   if member.name.startswith(environment.packages_path())]

    parsed = environment.parse(text.encode())
    # The framework's -- scfakebits, as cocotb would be -- is the image's.
    assert [str(pin) for pin in parsed.pins] == ["scfakeumi==0.3.1"]
    assert "example.com" not in text and "index" not in text.lower().replace(
        "indexes", "")
    assert text.startswith("# Generated by SiliconCompiler")
    assert f"{environment.packages_path()}/scfakeedit/__init__.py" in names
    assert all(member.isfile() for member in members)

    # And the create says so, for the refusal before the upload.
    assert run._python_env_files()


def two_testbenches(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    flow.node("sim", RunsATestbench())
    flow.node("sim2", RunsATestbench())
    flow.edge("sim", "sim2")
    project.set_flow(flow)
    project.option.set_nodashboard(True)
    project.option.set_builddir(os.path.abspath("build"))
    return project


def test_the_users_code_travels_once_and_a_node_of_only_that_gets_no_file(
        site, gcd_design, fake_v1, logged_in, monkeypatch):
    '''🔴 Once per job, and a file only for a node with a line to install:
    one whose only additions are the user's code has none, and needs no
    `python.env`.'''
    from siliconcompiler.remote.client.run import RemoteRun

    source = os.path.abspath("checkout")
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)
    monkeypatch.syspath_prepend(source)
    open("tb.py", "w").write("import scfakeedit\n")

    run = RemoteRun(two_testbenches(gcd_design), logged_in)
    run._collect()
    run._pack(__import__("pathlib").Path("upload.tar.gz"))

    with tarfile.open("upload.tar.gz") as tar:
        names = tar.getnames()

    assert names.count(f"{environment.packages_path()}/scfakeedit/__init__.py") == 1
    assert not [name for name in names if name.endswith(environment.FILENAME)]
    assert run._python_env_files() == {}


def test_only_a_node_the_run_executes_gets_a_file(
        site, gcd_design, fake_v1, logged_in):
    from siliconcompiler.remote.client.run import RemoteRun

    _distribution(site, "scfakeumi", "0.3.1")
    open("tb.py", "w").write("import scfakeumi\n")
    project = two_testbenches(gcd_design)
    project.set("option", "to", "sim")

    files = RemoteRun(project, logged_in)._python_env_files()

    assert set(files) == {("sim", "0")}


def test_a_compiled_package_fails_the_run_before_anything_moves(
        site, project, fake_v1, logged_in, monkeypatch):
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    source = os.path.abspath("checkout")
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)
    open(os.path.join(source, "scfakeedit", "_c.so"), "wb").write(b"\x7fELF")
    monkeypatch.syspath_prepend(source)
    open("tb.py", "w").write("import scfakeedit\n")

    with pytest.raises(RemoteError, match="sim/0: scfakeedit 2.0.0.*_c.so"):
        RemoteRun(project, logged_in)._python_env_files()


def test_two_nodes_sending_different_files_for_one_path_are_refused(
        site, gcd_design, fake_v1, logged_in, monkeypatch):
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    os.makedirs("other")
    open("tb.py", "w").write("import shared\n")
    open("shared.py", "w").write("ONE = 1\n")
    open("other/tb.py", "w").write("import shared\n")
    open("other/shared.py", "w").write("TWO = 2\n")
    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("twobenches")
    flow.node("sim", RunsATestbench())
    flow.node("sim2", Elsewhere())
    project.set_flow(flow)

    with pytest.raises(RemoteError, match="both be sent as shared.py"):
        RemoteRun(project, logged_in)._python_env_files()


def test_a_line_to_install_stops_before_create_where_the_server_installs_none(
        site, project, fake_v1, logged_in, capabilities):
    import responses

    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    _distribution(site, "scfakeumi", "0.3.1")
    open("tb.py", "w").write("import scfakeumi\n")
    fake_v1.replace(responses.GET, "", dict(capabilities, features=["logs.stream"]))

    with pytest.raises(RemoteError, match="sim/0 needs scfakeumi==0.3.1.*python.env"):
        RemoteRun(project, logged_in)._check_python_env()
    assert not [c for c in fake_v1.calls if c.request.method == "POST"
                and c.request.url.endswith("/v1/jobs")]


class CannotSetUpHere(RunsATestbench):
    def setup(self):
        raise RuntimeError("cocotb is not installed")


class Elsewhere(RunsATestbench):
    '''A testbench in another directory.'''

    def task(self):
        return "elsewhere"

    def get_python_environment(self):
        return PythonEnvironment(sources=(os.path.abspath("other/tb.py"),))


class Broken(NOPTask):
    def task(self):
        return "broken"

    def setup(self):
        raise RuntimeError("needs the image")


def test_a_node_running_the_users_python_that_cannot_be_worked_out_stops_the_run(
        site, gcd_design, fake_v1, logged_in):
    '''🔴 A node whose setup cannot run here, and that runs the user's
    Python: what it needs is unknown, so the client stops before create,
    naming it and why.'''
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    flow.node("sim", CannotSetUpHere())
    project.set_flow(flow)

    with pytest.raises(RemoteError, match="sim/0 runs your own Python.*cocotb is not installed"):
        RemoteRun(project, logged_in)._python_env_files()


def test_one_setup_that_cannot_run_drops_no_other_nodes_environment(
        site, gcd_design, fake_v1, logged_in):
    from siliconcompiler.remote.client.run import RemoteRun

    _distribution(site, "scfakeumi", "0.3.1")
    open("tb.py", "w").write("import scfakeumi\n")
    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    flow.node("sim", RunsATestbench())
    flow.node("other", Broken())
    project.set_flow(flow)

    files = RemoteRun(project, logged_in)._python_env_files()

    assert set(files) == {("sim", "0")}


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
    return outcome(server_client, key, token,
                   submit(server_client, key, token, job["id"], digest, size))


def test_the_users_code_beside_a_file_is_accepted(
        builds, server_client, key, token, job_archive, dispatcher, monkeypatch):
    pytest.importorskip("flask")
    from siliconcompiler.remote.server import envinstall

    monkeypatch.setattr(envinstall, "install",
                        lambda parsed, root, logger, node, constrain=(), indexes=():
                        str(__import__("pathlib").Path("site").mkdir(exist_ok=True) or "site"))
    response = _submitted(server_client, key, token, job_archive, {
        environment.path_for("stepone", "0"): b"numpy==2.0.1\n",
        f"{environment.packages_path()}/mine/__init__.py": b"VALUE = 1\n"})

    assert response.status_code == 202, response.get_json()


def test_the_users_code_with_no_file_is_accepted(
        server_client, key, token, job_archive, dispatcher):
    pytest.importorskip("flask")
    response = _submitted(server_client, key, token, job_archive, {
        f"{environment.packages_path()}/mine/__init__.py": b"VALUE = 1\n"})

    assert response.status_code == 202, response.get_json()


def test_the_old_layout_is_not_where_anything_goes(
        builds, server_client, key, token, job_archive, dispatcher):
    '''`python-env/` is not a member a first archive carries, and packages
    beside one node's file are not the job's packages.'''
    pytest.importorskip("flask")
    response = _submitted(server_client, key, token, job_archive, {
        "python-env/stepone/0/requirements.txt": b"numpy==2.0.1\n"})
    assert response.get_json()["reason"] == "unrequested_member"

    response = _submitted(server_client, key, token, job_archive, {
        "sc_python/nodes/stepone/0/packages/mine/__init__.py": b"VALUE = 1\n"})
    assert response.get_json()["reason"] == "environment_file"
