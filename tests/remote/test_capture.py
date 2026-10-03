import hashlib
import io
import json
import os
import sys
import tarfile

from importlib import metadata

import pytest
import responses

from siliconcompiler import Design, Flowgraph, Project
from siliconcompiler.remote import RemoteError, environment
from siliconcompiler.remote.client import capture, wheels
from siliconcompiler.remote.client.run import RemoteRun
from siliconcompiler.tool import PythonEnvironment
from siliconcompiler.tools.builtin.nop import NOPTask


# A job's Python, read off the submitting machine: index packages listed as
# installed, the rest built into wheels, the user's own modules sent beside
# their tests -- and never what the image holds.


def _distribution(site, name, version, requires=(), editable_source=None, archive=None,
                  files=None):
    '''An installed distribution in ``site``, as pip would leave it: from an
    index, or with ``editable_source`` installed editable from there, or with
    ``archive`` installed from that local file. ``files`` are its package's,
    beside ``__init__.py``.'''
    dist_info = os.path.join(site, f"{name}-{version}.dist-info")
    os.makedirs(dist_info)
    root = editable_source or site
    os.makedirs(os.path.join(root, name), exist_ok=True)
    package = {"__init__.py": "VALUE = 1\n", **(files or {})}
    for member, body in package.items():
        with open(os.path.join(root, name, member), "w") as f:
            f.write(body)
    meta = {"METADATA": f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
                        + "".join(f"Requires-Dist: {one}\n" for one in requires),
            "top_level.txt": f"{name}\n", "INSTALLER": "pip\n"}
    if editable_source:
        meta["direct_url.json"] = json.dumps({"url": f"file://{editable_source}",
                                              "dir_info": {"editable": True}})
    elif archive:
        meta["direct_url.json"] = json.dumps({"url": f"file://{archive}", "archive_info": {}})
    record = [f"{name}-{version}.dist-info/{entry},," for entry in
              ("METADATA", "top_level.txt", "INSTALLER", "RECORD")]
    if not editable_source:
        record += [f"{name}/{member},," for member in package]
    meta["RECORD"] = "\n".join(record) + "\n"
    for entry, body in meta.items():
        with open(os.path.join(dist_info, entry), "w") as f:
            f.write(body)
    return dist_info


# An in-tree PEP 517 backend: `pip wheel` builds it with no index or network.
_BACKEND = '''
import os
import zipfile

NAME, VERSION, TAG, REQUIRES = {name!r}, {version!r}, {tag!r}, {requires!r}
LEAVE_OUT = {leave_out!r}


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    here = os.path.dirname(os.path.abspath(__file__))
    filename = f"{{NAME}}-{{VERSION}}-{{TAG}}.whl"
    info = f"{{NAME}}-{{VERSION}}.dist-info"
    members = {{}}
    for root, dirs, files in os.walk(os.path.join(here, NAME)):
        for entry in files:
            if LEAVE_OUT and entry.endswith(LEAVE_OUT):
                continue
            full = os.path.join(root, entry)
            members[os.path.relpath(full, here).replace(os.sep, "/")] = open(full, "rb").read()
    members[f"{{info}}/METADATA"] = (f"Metadata-Version: 2.1\\nName: {{NAME}}\\n"
                                    f"Version: {{VERSION}}\\n" + "".join(
                                        f"Requires-Dist: {{one}}\\n" for one in REQUIRES)).encode()
    members[f"{{info}}/WHEEL"] = (f"Wheel-Version: 1.0\\nGenerator: test\\n"
                                 f"Root-Is-Purelib: true\\nTag: {{TAG}}\\n").encode()
    members[f"{{info}}/RECORD"] = "".join(f"{{member}},,\\n" for member in
                                          [*members, f"{{info}}/RECORD"]).encode()
    with zipfile.ZipFile(os.path.join(wheel_directory, filename), "w") as archive:
        for member, body in members.items():
            archive.writestr(member, body)
    return filename
'''


def editable_source(where, name, version, requires=(), tag="py3-none-any", leave_out=()):
    '''A project installed editable, whose packaging builds no file ending in
    one of ``leave_out``.'''
    os.makedirs(os.path.join(where, name), exist_ok=True)
    with open(os.path.join(where, "pyproject.toml"), "w") as f:
        f.write('[build-system]\nrequires = []\nbuild-backend = "backend"\n'
                'backend-path = ["."]\n')
    with open(os.path.join(where, "backend.py"), "w") as f:
        f.write(_BACKEND.format(name=name, version=version, tag=tag, requires=list(requires),
                                leave_out=tuple(leave_out)))
    return where


@pytest.fixture
def site(monkeypatch):
    site = os.path.abspath("site")
    os.makedirs(site)
    monkeypatch.syspath_prepend(site)
    # A real `pip wheel` finds nothing it was not handed.
    monkeypatch.setenv("PIP_NO_INDEX", "1")
    capture._module_distributions.cache_clear()
    yield site
    capture._module_distributions.cache_clear()


###########################
# What the code reaches
###########################

def test_what_a_source_imports_by_distribution(site):
    '''Absolute imports by top-level module, and the framework's; not relative
    ones or the standard library; what nothing installs is warned of.'''
    for name in ("scfakenumpy", "scfakescapy"):
        _distribution(site, name, "1.0")
    with open("tb.py", "w") as f:
        f.write("import os\nimport scfakenumpy.linalg\nfrom scfakescapy.all import IP\n"
                "from . import sibling\nimport scfakegone as c\n")

    found = capture.reach([os.path.abspath("tb.py")], ["scfakebits[fast]"])

    assert found.distributions == {"scfakenumpy": set(), "scfakescapy": set(),
                                   "scfakebits": {"fast"}}
    assert found.helpers == {}
    assert ["scfakegone" in warning for warning in found.warnings] == [True]


def test_a_helper_beside_the_test_is_the_users_own_before_any_distribution(site):
    '''The test's folder is first on the tool's path, so a module there
    shadows an installed one -- and its own imports are looked up there too.'''
    _distribution(site, "tbutil", "9.9")
    _distribution(site, "scfakeumi", "0.3.1")
    os.makedirs("bench/mylib/sub")
    open("bench/tb.py", "w").write("import tbutil\nimport mylib\n")
    open("bench/tbutil.py", "w").write("import scfakeumi\n")
    open("bench/mylib/__init__.py", "w").write("from mylib import sub\n")
    open("bench/mylib/sub/__init__.py", "w").write("import tbutil\n")
    open("bench/mylib/data.txt", "w").write("carried with the package\n")
    os.symlink("data.txt", "bench/mylib/linked.txt")

    test = os.path.abspath("bench/tb.py")
    found = capture.reach([test])

    assert found.distributions == {"scfakeumi": set()}
    assert sorted(found.helpers[test]) == ["mylib/__init__.py", "mylib/data.txt",
                                           "mylib/sub/__init__.py", "tbutil.py"]
    assert any("linked.txt is a link" in warning for warning in found.warnings)


def test_an_import_under_a_platform_check_is_not_followed(site):
    '''Either branch may not be the server's platform: neither is listed, and
    each installed one is said, unless an unconditional import lists it.'''
    for name in ("scfakewin", "scfakeposix", "scfakeboth"):
        _distribution(site, name, "1.0")
    open("tb.py", "w").write(
        "import sys\nimport platform\nimport scfakeboth\n"
        "if sys.platform == 'win32':\n    import scfakewin\n"
        "else:\n    from scfakeposix import thing\n"
        "def later():\n"
        "    if platform.system() == 'Linux':\n        import scfakeboth\n"
        "        import scfakenowhere\n")

    found = capture.reach([os.path.abspath("tb.py")])

    assert found.distributions == {"scfakeboth": set()}
    assert [warning.split(" imports ")[1].split()[0] for warning in found.warnings] == \
        ["scfakeposix", "scfakewin"]
    assert all("only under a platform check" in warning for warning in found.warnings)


def test_a_test_module_that_cannot_be_read_stops_the_work(site):
    open("tb.py", "w").write("def broken(:\n")
    with pytest.raises(capture.CannotForward, match="cannot be read as Python"):
        capture.reach([os.path.abspath("tb.py")])


###########################
# The lists
###########################

def test_the_lists_are_what_the_code_reaches_and_what_that_depends_on(site):
    '''🔴 Canonical names at installed versions, constraining only what the
    install needs through `Requires-Dist` -- never the rest of this machine.'''
    _distribution(site, "SCFake_Umi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0", requires=["scfakedeep>=1"])
    _distribution(site, "scfakedeep", "4.0")
    _distribution(site, "scfakeunrelated", "9.0")

    listed = capture.lists({"scfake-umi": set(), "pytest": set()}, ["pytest"])

    assert listed.requirements == [("scfake-umi", "0.3.1")]
    assert listed.constraints == [("scfakebits", "1.2.0"), ("scfakedeep", "4.0")]
    for name, version in listed.requirements + listed.constraints:
        environment.parse_entry(f"{name}=={version}")


def test_what_no_index_can_supply_is_a_wheel_and_what_it_depends_on_is_constrained(site):
    _distribution(site, "scfakeedit", "2.0.0", editable_source=os.path.abspath("checkout"),
                  requires=["scfakedep", "scfakeidx"])
    _distribution(site, "scfakedep", "1.0.0", archive=os.path.abspath("scfakedep.tar.gz"))
    _distribution(site, "scfakeidx", "1.1")
    # Installed from a local source and reached by nothing: in no list.
    _distribution(site, "scfakeloose", "3.0.0", archive=os.path.abspath("loose.tar.gz"))

    listed = capture.lists({"scfakeedit": set()}, [])

    assert [one.metadata["Name"] for one in listed.wheels] == ["scfakedep", "scfakeedit"]
    assert (listed.requirements, listed.constraints) == ([], [("scfakeidx", "1.1")])


def test_a_listed_distribution_installing_a_pth_file_is_warned_of(site):
    '''Warned, not stopped: an index package whose `.pth` runs in the node.'''
    info = _distribution(site, "scfakehooked", "1.0")
    open(os.path.join(site, "scfakehooked.pth"), "w").write("import scfakehooked\n")
    with open(os.path.join(info, "RECORD"), "a") as f:
        f.write("scfakehooked.pth,,\n")

    listed = capture.lists({"scfakehooked": set()}, [])

    assert listed.requirements == [("scfakehooked", "1.0")]
    assert listed.warnings == [
        "scfakehooked installs scfakehooked.pth, a .pth file, which runs in every "
        "Python that starts with it on its path -- the node's among them"]


def test_a_closure_past_the_servers_bounds_stops_the_run(site, monkeypatch):
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0")
    monkeypatch.setattr(environment, "MAX_ENTRIES", 1)
    with pytest.raises(capture.CannotForward,
                       match="reaches 2 installed distributions.*at most 1"):
        capture.lists({"scfakeumi": set()}, [])


###########################
# The wheels
###########################

def test_an_install_from_a_local_file_is_repacked_as_a_pure_wheel(site):
    '''What was installed and its metadata, nothing pip wrote at install, and
    the same bytes each time so the server builds its install once.'''
    import zipfile

    _distribution(site, "scfakeloose", "3.0.0", archive=os.path.abspath("loose.tar.gz"),
                  files={"data.txt": "a data file\n"})
    os.makedirs("one")
    os.makedirs("two")

    first = wheels.build(metadata.distribution("scfakeloose"), "one")
    second = wheels.build(metadata.distribution("scfakeloose"), "two")

    assert os.path.basename(first) == "scfakeloose-3.0.0-py3-none-any.whl"
    assert environment.check_wheel(first).name == "scfakeloose"
    with zipfile.ZipFile(first) as archive:
        members = sorted(archive.namelist())
    assert members == ["scfakeloose-3.0.0.dist-info/METADATA",
                       "scfakeloose-3.0.0.dist-info/RECORD",
                       "scfakeloose-3.0.0.dist-info/WHEEL",
                       "scfakeloose-3.0.0.dist-info/top_level.txt",
                       "scfakeloose/__init__.py", "scfakeloose/data.txt"]
    assert open(first, "rb").read() == open(second, "rb").read()


@pytest.mark.parametrize("change,why", [
    (dict(files={"_c.so": "\x7fELF"}), r"scfakehook 1\.0\.0.*_c\.so"),
    (dict(files={"_hook.pth": "import os\n"}), r"_hook\.pth, a \.pth file"),
    (dict(requires=["scfakebits @ file:///home/someone/bits"]), "dependency by URL"),
], ids=["compiled", "pth", "url"])
def test_a_wheel_the_server_would_reject_is_refused_before_anything_is_built(
        site, change, why):
    '''D292: a compiled file, a file that runs by itself, a dependency by URL --
    named, before anything is created.'''
    _distribution(site, "scfakehook", "1.0.0", archive=os.path.abspath("h.tar.gz"),
                  **change)
    with pytest.raises(capture.CannotForward, match=why):
        wheels.build(metadata.distribution("scfakehook"), ".")


def test_an_editable_install_is_built_from_its_source_naming_what_it_leaves_out(site):
    '''`pip wheel --no-deps`, for real. The node has only the wheel: each
    module file it leaves out is named, and the wheel still goes.'''
    pytest.importorskip("pip")
    source = editable_source(os.path.abspath("checkout"), "scfakeedit", "2.0.0",
                             requires=["scfakebits>=1"], leave_out=(".dat",))
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source,
                  files={"table.dat": "1 2 3\n", "more.dat": "4\n"})
    open(os.path.join(source, "scfakeedit", ".hidden"), "w").write("")
    warned = []

    path = wheels.build(metadata.distribution("scfakeedit"), ".", warn=warned.append)

    assert os.path.basename(path) == "scfakeedit-2.0.0-py3-none-any.whl"
    assert environment.check_wheel(path).version == "2.0.0"
    assert len(warned) == 1
    assert "leaves out scfakeedit/more.dat, scfakeedit/table.dat, which" in warned[0]


@pytest.mark.parametrize("tag,backend,why", [
    ("cp312-cp312-linux_x86_64", None, "only a pure wheel"),
    ("py3-none-any", "raise ImportError('no backend')\n", "pip wheel --no-deps.*failed"),
], ids=["not-pure", "build-fails"])
def test_an_editable_build_that_is_not_a_pure_wheel_stops_with_why(site, tag, backend, why):
    pytest.importorskip("pip")
    source = editable_source(os.path.abspath("checkout"), "scfakeedit", "2.0.0", tag=tag)
    if backend:
        open(os.path.join(source, "backend.py"), "w").write(backend)
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)
    with pytest.raises(capture.CannotForward, match=why):
        wheels.build(metadata.distribution("scfakeedit"), ".")
    assert not [name for name in os.listdir(".") if name.endswith(".whl")]


###########################
# The task's half
###########################

class RunsATestbench(NOPTask):
    '''A task whose tool runs a testbench of the user's.'''

    def task(self):
        return "runsatestbench"

    def get_python_environment(self):
        return PythonEnvironment(sources=(os.path.abspath("tb.py"),),
                                 framework=("scfakebits",))


def cocotb_project(test_body, helpers=None):
    '''A cocotb testbench, its test module and the helpers beside it.'''
    from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask

    os.makedirs("bench", exist_ok=True)
    open("bench/test_gcd.py", "w").write(test_body)
    for name, body in (helpers or {}).items():
        os.makedirs(os.path.dirname(os.path.join("bench", name)) or "bench", exist_ok=True)
        open(os.path.join("bench", name), "w").write(body)

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


def test_a_cocotb_node_names_its_testbench_and_leaves_cocotb_to_the_image():
    '''This process sets the GPI up from its own cocotb, so the image holds it.'''
    from siliconcompiler.scheduler import SchedulerNode
    node = SchedulerNode(cocotb_project("import cocotb\n"), "sim", "0")
    with node.runtime():
        wanted = node.task.get_python_environment()
    assert [os.path.basename(path) for path in wanted.sources] == ["test_gcd.py"]
    assert wanted.framework == ("cocotb",)


###########################
# The client, end to end
###########################

@pytest.fixture
def offers_python_env(fake_v1, capabilities):
    fake_v1.replace(responses.GET, "", dict(
        capabilities, features=capabilities["features"] + ["python.env"]))


def _routes_for_a_submit(fake_v1):
    fake_v1.route(responses.POST, "jobs",
                  {"id": "01J9-job", "state": "created", "project": None,
                   "created_at": "2026-09-22T10:00:00.000Z"}, status=201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit",
                  {"id": "01J9-job", "state": "staging", "terminal": False}, status=202)


def _put_body(fake_v1):
    put = next(c for c in fake_v1.calls if c.request.url == "https://storage.test/put")
    return put.request.body.read() if hasattr(put.request.body, "read") else put.request.body


def _uploaded(fake_v1):
    with tarfile.open(fileobj=io.BytesIO(_put_body(fake_v1))) as tar:
        return {member.name: (tar.extractfile(member).read() if member.isfile() else None)
                for member in tar.getmembers()}


def _created(fake_v1):
    return [c for c in fake_v1.calls
            if c.request.method == "POST" and c.request.url.endswith("/v1/jobs")]


def test_a_cocotb_job_with_an_index_package_and_an_editable_helper_package(
        site, fake_v1, logged_in, offers_python_env):
    '''🔴 The index package listed as installed; the editable one a wheel in
    neither list; the helper beside the test; cocotb left to the image.'''
    pytest.importorskip("pip")

    _distribution(site, "scfakebits", "1.2.0")
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    source = editable_source(os.path.abspath("checkout"), "scfake_helper", "0.1.0",
                             requires=["scfakebits>=1"])
    _distribution(site, "scfake_helper", "0.1.0", editable_source=source)
    project = cocotb_project("import cocotb\nimport scfakebits\nimport scfake_helper\n"
                             "import tbutil\n", {"tbutil.py": "import scfakeumi\n"})
    _routes_for_a_submit(fake_v1)

    RemoteRun(project, logged_in)._start()

    body = json.loads(_created(fake_v1)[0].request.body)
    member = body["python_packages"]
    assert member["requirements"] == ["scfakebits==1.2.0", "scfakeumi==0.3.1"]
    listed = {entry.split("==")[0] for entry in member["constraints"]}
    assert not listed & {"cocotb", "siliconcompiler", "scfake-helper", "scfakebits"}
    assert "python.env" in body["descriptor"]["needs"]
    assert "cocotb" in body["descriptor"]["requested_versions"]["python"]
    # The Python its modules were written for: this one's major.minor (D293).
    assert body["descriptor"]["requested_versions"]["interpreter"] == {
        "python": [f"=={sys.version_info[0]}.{sys.version_info[1]}.*"]}

    members = _uploaded(fake_v1)
    wheel = f"sc_collected_files/{environment.WHEELS}/scfake_helper-0.1.0-py3-none-any.whl"
    assert wheel in members
    test, = [name for name in members if name.endswith("/test_gcd.py")]
    assert members[f"{os.path.dirname(test)}/tbutil.py"] == b"import scfakeumi\n"
    assert not [name for name in members if name.startswith("sc_python")]


def test_a_compiled_local_package_is_refused_before_create(
        site, fake_v1, logged_in, offers_python_env):
    _distribution(site, "scfakec", "1.0.0", archive=os.path.abspath("c.tar.gz"),
                  files={"_c.so": "\x7fELF"})
    project = cocotb_project("import scfakec\n")
    with pytest.raises(RemoteError, match="scfakec 1.0.0.*compiled file.*_c.so"):
        RemoteRun(project, logged_in)._preflight()
    assert not _created(fake_v1)


def test_a_helper_holding_a_compiled_extension_is_refused(site, fake_v1, logged_in):
    project = cocotb_project("import mine\n", {"mine/__init__.py": "", "mine/_c.so": "x"})
    with pytest.raises(RemoteError, match="compiled extension"):
        RemoteRun(project, logged_in)._python()


def test_packages_to_install_stop_before_create_where_the_server_installs_none(
        site, fake_v1, logged_in):
    _distribution(site, "scfakeumi", "0.3.1")
    project = cocotb_project("import scfakeumi\n")
    with pytest.raises(RemoteError, match="needs scfakeumi==0.3.1.*python.env"):
        RemoteRun(project, logged_in)._check_python_env()
    assert not _created(fake_v1)


def test_a_flow_needing_no_package_lists_nothing_and_its_helpers_still_travel(
        site, gcd_nop_project, fake_v1, logged_in):
    '''A task runs none of the user's Python by default; a testbench of only
    its own modules needs no `python_packages` and no `python.env`.'''
    assert NOPTask().get_python_environment() is None
    assert RemoteRun(gcd_nop_project, logged_in)._python() == (None, {}, {})

    project = cocotb_project("import cocotb\nimport tbutil\n", {"tbutil.py": "X = 1\n"})
    member, built, helpers = RemoteRun(project, logged_in)._python()
    assert (member, built) == (None, {})
    assert [os.path.basename(path) for path in helpers] == ["tbutil.py"]


class CannotSetUpHere(RunsATestbench):
    def setup(self):
        raise RuntimeError("cocotb is not installed")


class Broken(NOPTask):
    def task(self):
        return "broken"

    def setup(self):
        raise RuntimeError("needs the image")


def tb_project(gcd_design, **nodes):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    for step, task in nodes.items():
        flow.node(step, task)
    project.set_flow(flow)
    return project


def test_a_node_running_the_users_python_that_cannot_be_worked_out_stops_the_run(
        site, gcd_design, fake_v1, logged_in):
    '''🔴 Its setup cannot run here: stop before create, naming it and why.
    A failing setup elsewhere drops no other node's Python.'''
    with pytest.raises(RemoteError, match="sim/0 runs your own Python.*cocotb is not installed"):
        RemoteRun(tb_project(gcd_design, sim=CannotSetUpHere()), logged_in)._python()
    _distribution(site, "scfakeumi", "0.3.1")
    open("tb.py", "w").write("import scfakeumi\n")
    project = tb_project(gcd_design, sim=RunsATestbench(), other=Broken())
    member, _, _ = RemoteRun(project, logged_in)._python()
    assert member["requirements"] == ["scfakeumi==0.3.1"]


def test_a_python_entry_is_answered_with_a_repacked_wheel(site, fake_v1, logged_in,
                                                          tmp_path):
    '''Repacked from the install here. D306: asked at create, in the first
    archive beside the manifest; asked later, alone in the follow-up.'''
    from siliconcompiler.utils.paths import collectiondir

    _distribution(site, "scfake_private", "1.2.0")
    project = cocotb_project("import scfake_private\n")
    _routes_for_a_submit(fake_v1)
    wheel = f"sc_collected_files/{environment.WHEELS}/scfake_private-1.2.0-py3-none-any.whl"
    asked = [{"kind": "python", "name": "scfake-private"}]

    run = RemoteRun(project, logged_in)
    run._asked_rows = run._answer(asked, collectiondir(project))
    run._pack(tmp_path / "first.tar.gz")
    with tarfile.open(tmp_path / "first.tar.gz") as tar:
        assert {wheel, f"{project.name}.pkg.json"} <= set(tar.getnames())

    RemoteRun(project, logged_in)._send_asked("01J9-job", asked)

    members = _uploaded(fake_v1)
    assert [name for name in members if members[name] is not None] == [wheel]
    grant = next(c for c in fake_v1.calls if "upload-grant" in c.request.path_url)
    assert json.loads(grant.request.body)["digest"] == \
        f"sha256:{hashlib.sha256(_put_body(fake_v1)).hexdigest()}"


def test_a_compiled_package_asked_for_stops_and_cancels_the_job(site, fake_v1, logged_in):
    _distribution(site, "scfakec", "1.0.0", files={"_c.so": "x"})
    project = cocotb_project("import scfakec\n")
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                  {"id": "01J9-job", "state": "cancelled", "terminal": True}, status=202)

    with pytest.raises(RemoteError, match="scfakec.*compiled file"):
        RemoteRun(project, logged_in)._send_asked(
            "01J9-job", [{"kind": "python", "name": "scfakec"}])
    cancel, = [c for c in fake_v1.calls if c.request.path_url.endswith("/cancel")]
    assert "the Python package scfakec: it holds a compiled file, scfakec/_c.so" in \
        json.loads(cancel.request.body)["reason"]
    assert not [c for c in fake_v1.calls if "upload-grant" in c.request.path_url]


###########################
# What the account may do, and what the job ran
###########################

@pytest.mark.parametrize("granted,wheel,stops", [
    # No `authorized`, as sc-server's: nothing granted gates nothing.
    (None, False, None),
    ([{"name": "python-packages", "via": ["self"]}], False, None),
    ([], False, "is not granted python-packages"),
    ([{"name": "python-packages", "via": ["self"]}], True,
     "python-wheels to upload scfakeloose-3.0.0-py3-none-any.whl.*not granted python-wheels"),
    # Each document in the way, by its `terms` title or its id (D309).
    ([{"name": "python-packages", "via": ["self"], "blocked_by": ["py-terms"]}], False,
     "holds python-packages blocked on an agreement.*sign The Python terms"),
    ([{"name": "python-packages", "via": ["self"], "blocked_by": ["other-terms"]}], False,
     "blocked on an agreement.*sign other-terms"),
    # The old name grants nothing.
    ([{"name": "python-env", "via": ["self"]}], False, "is not granted python-packages"),
])
def test_a_capability_the_account_lacks_stops_the_run_before_create(
        site, fake_v1, logged_in, granted, wheel, stops):
    '''Checked against `GET /v1/me`'s `authorized.capabilities` before create:
    packages need `python-packages`, wheels `python-wheels`.'''
    _distribution(site, "scfakeumi", "0.3.1")
    _distribution(site, "scfakeloose", "3.0.0", archive=os.path.abspath("loose.tar.gz"))
    project = cocotb_project("import scfakeumi\n" + ("import scfakeloose\n" if wheel else ""))
    me = {"id": "u-1", "terms": [{"id": "py-terms", "title": "The Python terms"}]}
    if granted is not None:
        me["authorized"] = {"pdks": [], "capabilities": granted}
    fake_v1.route(responses.GET, "me", me)
    run = RemoteRun(project, logged_in)

    if stops is None:
        run._check_account()
    else:
        with pytest.raises(RemoteError, match=stops):
            run._check_account()
    assert not _created(fake_v1)


@pytest.mark.parametrize("resource,advice", [
    ("python-packages", "Ask the deployment for the python-packages grant. A job whose "
                        "only Python is its own modules needs none."),
    ("python-wheels", "Ask the deployment for the python-wheels grant, or publish the "
                      "package to one of its indexes."),
])
def test_a_capability_refused_at_create_says_which_and_what_to_do(
        site, fake_v1, logged_in, offers_python_env, resource, advice):
    '''A deployment that grants capabilities refuses at create or on the job --
    the same refusal either way.'''
    from conftest import problem
    from siliconcompiler.remote.client.errors import ServerProblem, describe

    refusal = problem("entitlement-denied", 403, resource_kind="capability",
                      resource=resource, detail=f"this account holds no {resource}")
    _distribution(site, "scfakeumi", "0.3.1")
    project = cocotb_project("import scfakeumi\n")
    fake_v1.route(responses.GET, "me", {"id": "u-1"})
    fake_v1.route(responses.POST, "jobs", refusal, status=403,
                  content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        RemoteRun(project, logged_in)._start()

    said = str(raised.value)
    assert f"resource: {resource}" in said and "resource_kind: capability" in said
    assert advice in said
    assert advice in describe(refusal)
    assert not [c for c in fake_v1.calls if "upload-grant" in c.request.url]


def test_what_the_job_ran_in_place_of_a_listed_version_is_said_once(
        site, fake_v1, logged_in, caplog):
    '''Once staged: each listed version its images hold another of, beside the
    one listed here. What matches is not said.'''
    import logging

    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0")
    run = RemoteRun(cocotb_project("import scfakeumi\n"), logged_in)
    run._python()
    ran = {"state": "running",
           "resolved_versions": {"python": {"scfakeumi": ["0.3.4"], "SCFakeBits": ["1.2"],
                                            "siliconcompiler": ["0.38.9"]}}}

    with caplog.at_level(logging.WARNING):
        run._say_substituted({"state": "staging"})
        run._say_substituted(ran)
        run._say_substituted(ran)

    said = [record.getMessage() for record in caplog.records
            if "in place of" in record.getMessage()]
    assert said == ["This job runs scfakeumi 0.3.4, in place of 0.3.1 as installed here"]
