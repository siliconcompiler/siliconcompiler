import hashlib
import io
import json
import os
import sys
import tarfile

import pytest

from siliconcompiler import Design, Flowgraph, Project
from siliconcompiler.remote import environment
from siliconcompiler.remote.client import capture, wheels
from siliconcompiler.tool import PythonEnvironment
from siliconcompiler.tools.builtin.nop import NOPTask


# A job's Python, read off the submitting machine (surface *A node's own Python
# packages, built while staging*): what an index can supply listed in the
# create body at the version installed here, what none can built into a wheel,
# the user's own modules sent beside their tests -- and never what the image
# holds.


def _distribution(site, name, version, requires=(), editable_source=None, archive=None,
                  files=None):
    '''An installed distribution in ``site``, as pip would leave it: from an
    index, or with ``editable_source`` installed editable from there, or with
    ``archive`` installed from that local file. ``files`` are its package's,
    beside ``__init__.py``.'''
    dist_info = os.path.join(site, f"{name}-{version}.dist-info")
    os.makedirs(dist_info)
    with open(os.path.join(dist_info, "METADATA"), "w") as f:
        f.write(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        for requirement in requires:
            f.write(f"Requires-Dist: {requirement}\n")
    with open(os.path.join(dist_info, "top_level.txt"), "w") as f:
        f.write(f"{name}\n")

    root = editable_source or site
    os.makedirs(os.path.join(root, name), exist_ok=True)
    package = {"__init__.py": "VALUE = 1\n", **(files or {})}
    for member, body in package.items():
        with open(os.path.join(root, name, member), "w") as f:
            f.write(body)
    record = [f"{name}-{version}.dist-info/{entry},," for entry in
              ("METADATA", "top_level.txt", "INSTALLER", "RECORD")]
    open(os.path.join(dist_info, "INSTALLER"), "w").write("pip\n")
    if not editable_source:
        record += [f"{name}/{member},," for member in package]
    if editable_source:
        with open(os.path.join(dist_info, "direct_url.json"), "w") as f:
            json.dump({"url": f"file://{editable_source}", "dir_info": {"editable": True}}, f)
    elif archive:
        with open(os.path.join(dist_info, "direct_url.json"), "w") as f:
            json.dump({"url": f"file://{archive}", "archive_info": {}}, f)
    with open(os.path.join(dist_info, "RECORD"), "w") as f:
        f.write("\n".join(record) + "\n")
    return dist_info


# An in-tree PEP 517 backend: `pip wheel` builds it with nothing to install
# first, so a test of the real build needs no index and no network.
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
    '''A project a user installed editable: its package, and packaging of
    its own -- which builds no file ending in one of ``leave_out``.'''
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


def dist(name):
    from importlib import metadata

    return metadata.distribution(name)


###########################
# What the code reaches
###########################

def test_what_a_source_imports(site):
    '''Absolute imports, by their top-level module; a relative one is the
    source's own package, and the standard library is left out.'''
    for name in ("scfakenumpy", "scfakescapy"):
        _distribution(site, name, "1.0")
    with open("tb.py", "w") as f:
        f.write("import os\nimport scfakenumpy.linalg\nfrom scfakescapy.all import IP\n"
                "from . import sibling\nimport scfakegone as c\n")

    found = capture.reach([os.path.abspath("tb.py")])

    assert found.distributions == {"scfakenumpy": set(), "scfakescapy": set()}
    assert ["scfakegone" in warning for warning in found.warnings] == [True]


def test_what_the_imports_reach_by_distribution(site):
    _distribution(site, "scfakeumi", "0.3.1")
    open("tb.py", "w").write("import scfakeumi\nimport json\nimport scfakenowhere\n")

    found = capture.reach([os.path.abspath("tb.py")], ["scfakebits[fast]"])

    assert found.distributions == {"scfakeumi": set(), "scfakebits": {"fast"}}
    assert found.helpers == {}
    assert "scfakenowhere" in found.warnings[0]


def test_a_helper_beside_the_test_is_the_users_own_before_any_distribution(site):
    '''As Python finds it: the test's folder is first on the tool's path, so
    a module there shadows an installed one of the same name -- and its own
    imports are looked up there too.'''
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
    '''Either branch is for a platform the server's may not be, so neither
    is listed -- and said, where it names something installed here, unless
    an unconditional import lists it anyway.'''
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
    '''🔴 Canonical names at canonical versions -- what the server's grammar
    takes -- never a `requested_versions.python` name, and a constraint only
    on what the install needs, followed through `Requires-Dist`: never on
    everything else this machine holds.'''
    _distribution(site, "SCFake_Umi", "0.3.1", requires=["scfakebits"])
    _distribution(site, "scfakebits", "1.2.0", requires=["scfakedeep>=1"])
    _distribution(site, "scfakedeep", "4.0")
    _distribution(site, "scfakeunrelated", "9.0")

    listed = capture.lists({"scfake-umi": set(), "pytest": set()}, ["pytest"])

    assert listed.requirements == [("scfake-umi", "0.3.1")]
    assert listed.constraints == [("scfakebits", "1.2.0"), ("scfakedeep", "4.0")]
    for name, version in listed.requirements + listed.constraints:
        environment.parse_entry(f"{name}=={version}")


def test_what_a_wheel_depends_on_is_constrained_too(site):
    _distribution(site, "scfakeedit", "2.0.0", editable_source=os.path.abspath("checkout"),
                  requires=["scfakeidx"])
    _distribution(site, "scfakeidx", "1.1")

    listed = capture.lists({"scfakeedit": set()}, [])

    assert [one.metadata["Name"] for one in listed.wheels] == ["scfakeedit"]
    assert (listed.requirements, listed.constraints) == ([], [("scfakeidx", "1.1")])


def test_a_listed_distribution_installing_a_pth_file_is_warned_of(site):
    '''Warned, and not stopped: an index's package the server installs with
    the rest, whose `.pth` then runs in the node's Python.'''
    info = _distribution(site, "scfakehooked", "1.0")
    open(os.path.join(site, "scfakehooked.pth"), "w").write("import scfakehooked\n")
    with open(os.path.join(info, "RECORD"), "a") as f:
        f.write("scfakehooked.pth,,\n")

    listed = capture.lists({"scfakehooked": set()}, [])

    assert listed.requirements == [("scfakehooked", "1.0")]
    assert listed.warnings == [
        "scfakehooked installs scfakehooked.pth, a .pth file, which runs in every "
        "Python that starts with it on its path -- the node's among them"]


def test_what_no_index_can_supply_is_a_wheel_and_in_neither_list(site):
    source = os.path.abspath("checkout")
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source,
                  requires=["scfakedep"])
    _distribution(site, "scfakedep", "1.0.0", archive=os.path.abspath("scfakedep.tar.gz"))
    _distribution(site, "scfakeloose", "3.0.0", archive=os.path.abspath("loose.tar.gz"))

    listed = capture.lists({"scfakeedit": set()}, [])

    assert [one.metadata["Name"] for one in listed.wheels] == ["scfakedep", "scfakeedit"]
    names = {name for name, _ in listed.requirements + listed.constraints}
    # Installed from a local source and reached by nothing: in neither.
    assert not names & {"scfakeedit", "scfakedep", "scfakeloose"}


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
    '''What was installed, and its metadata; none of what pip wrote at
    install; the same bytes each time, so the server builds its install once.'''
    import zipfile

    _distribution(site, "scfakeloose", "3.0.0", archive=os.path.abspath("loose.tar.gz"),
                  files={"data.txt": "a data file\n"})
    os.makedirs("one")
    os.makedirs("two")

    first = wheels.build(dist("scfakeloose"), "one")
    second = wheels.build(dist("scfakeloose"), "two")

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


def test_a_compiled_file_is_refused_before_anything_is_built(site):
    _distribution(site, "scfakec", "1.0.0", archive=os.path.abspath("c.tar.gz"),
                  files={"_c.so": "\x7fELF"})

    with pytest.raises(capture.CannotForward, match="scfakec 1.0.0.*_c.so"):
        wheels.build(dist("scfakec"), ".")


@pytest.mark.parametrize("change,why", [
    (dict(files={"_hook.pth": "import os\n"}), r"_hook\.pth, a \.pth file"),
    (dict(requires=["scfakebits @ file:///home/someone/bits"]), "dependency by URL"),
])
def test_a_wheel_the_server_would_reject_is_refused_before_create(site, change, why):
    '''surface D292: the client refuses what the server rejects after the upload
    -- a file that runs by itself, a dependency by URL -- naming it, and
    before anything is created.'''
    _distribution(site, "scfakehook", "1.0.0", archive=os.path.abspath("h.tar.gz"),
                  **change)

    with pytest.raises(capture.CannotForward, match=why):
        wheels.build(dist("scfakehook"), ".")


def test_an_editable_install_is_built_from_its_source(site, monkeypatch):
    '''`pip wheel --no-deps`, for real: the project's own packaging.'''
    pytest.importorskip("pip")
    source = editable_source(os.path.abspath("checkout"), "scfakeedit", "2.0.0",
                             requires=["scfakebits>=1"])
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)

    path = wheels.build(dist("scfakeedit"), ".")

    assert os.path.basename(path) == "scfakeedit-2.0.0-py3-none-any.whl"
    assert environment.check_wheel(path).version == "2.0.0"


def test_an_editable_build_leaving_out_what_its_module_holds_is_warned_of(site):
    '''The run here imports from the module directory, and the node has
    only the wheel: each file the packaging leaves out, named -- and the
    wheel still goes.'''
    pytest.importorskip("pip")
    source = editable_source(os.path.abspath("checkout"), "scfakeedit", "2.0.0",
                             leave_out=(".dat",))
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source,
                  files={"table.dat": "1 2 3\n", "more.dat": "4\n"})
    open(os.path.join(source, "scfakeedit", ".hidden"), "w").write("")
    warned = []

    path = wheels.build(dist("scfakeedit"), ".", warn=warned.append)

    assert os.path.isfile(path)
    assert len(warned) == 1
    assert "leaves out scfakeedit/more.dat, scfakeedit/table.dat, which" in warned[0]


def test_an_editable_build_that_is_not_pure_is_refused(site):
    pytest.importorskip("pip")
    source = editable_source(os.path.abspath("checkout"), "scfakeedit", "2.0.0",
                             tag="cp312-cp312-linux_x86_64")
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)

    with pytest.raises(capture.CannotForward, match="only a pure wheel"):
        wheels.build(dist("scfakeedit"), ".")
    assert not [name for name in os.listdir(".") if name.endswith(".whl")]


def test_a_build_that_fails_stops_with_its_error(site):
    pytest.importorskip("pip")
    source = editable_source(os.path.abspath("checkout"), "scfakeedit", "2.0.0")
    open(os.path.join(source, "backend.py"), "w").write("raise ImportError('no backend')\n")
    _distribution(site, "scfakeedit", "2.0.0", editable_source=source)

    with pytest.raises(capture.CannotForward, match="pip wheel --no-deps.*failed"):
        wheels.build(dist("scfakeedit"), ".")


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


def test_a_task_runs_none_of_the_users_python_by_default():
    assert NOPTask().get_python_environment() is None


def test_a_cocotb_node_names_its_testbench_and_leaves_cocotb_to_the_image():
    '''cocotb is SiliconCompiler's for a cocotb task: this process sets the
    GPI up from its own copy, so the image holds it and the lists leave it
    out.'''
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
# The client, end to end
###########################

def cocotb_project(test_body, helpers=None):
    '''A cocotb testbench, its test module and the helpers beside it, as a
    user writes them.'''
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


@pytest.fixture
def offers_python_env(fake_v1, capabilities):
    import responses

    fake_v1.replace(responses.GET, "", dict(
        capabilities, features=capabilities["features"] + ["python.env"]))


def _routes_for_a_submit(fake_v1):
    import responses

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


def _uploaded(fake_v1):
    put = next(c for c in fake_v1.calls if c.request.url == "https://storage.test/put")
    body = put.request.body.read() if hasattr(put.request.body, "read") else put.request.body
    with tarfile.open(fileobj=io.BytesIO(body)) as tar:
        return {member.name: (tar.extractfile(member).read() if member.isfile() else None)
                for member in tar.getmembers()}


def test_a_cocotb_job_with_an_index_package_and_an_editable_helper_package(
        site, fake_v1, logged_in, offers_python_env):
    '''🔴 One job's Python through the client for real: the package an index
    supplies listed at the version installed here; the editable package built
    into a wheel with `pip wheel`, and in neither list; the test's own helper
    module in the test's collected folder under its own name; cocotb left to
    the image; and the create saying all of it.'''
    pytest.importorskip("pip")
    from siliconcompiler.remote.client.run import RemoteRun

    _distribution(site, "scfakebits", "1.2.0")
    _distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits"])
    source = editable_source(os.path.abspath("checkout"), "scfake_helper", "0.1.0",
                             requires=["scfakebits>=1"])
    _distribution(site, "scfake_helper", "0.1.0", editable_source=source)
    project = cocotb_project("import cocotb\nimport scfakebits\nimport scfake_helper\n"
                             "import tbutil\n", {"tbutil.py": "import scfakeumi\n"})
    _routes_for_a_submit(fake_v1)

    run = RemoteRun(project, logged_in)
    run._start()

    create = next(c for c in fake_v1.calls if c.request.method == "POST"
                  and c.request.url.endswith("/v1/jobs"))
    body = json.loads(create.request.body)
    member = body["python_packages"]
    assert member["requirements"] == ["scfakebits==1.2.0", "scfakeumi==0.3.1"]
    listed = {entry.split("==")[0] for entry in member["constraints"]}
    assert not listed & {"cocotb", "siliconcompiler", "scfake-helper", "scfakebits"}
    assert "python.env" in body["descriptor"]["needs"]
    assert "cocotb" in body["descriptor"]["requested_versions"]["python"]
    # A node runs the user's Python, so the job names the Python its modules
    # were written for: this one's major and minor (surface D293).
    assert body["descriptor"]["requested_versions"]["interpreter"] == {
        "python": [f"=={sys.version_info[0]}.{sys.version_info[1]}.*"]}

    members = _uploaded(fake_v1)
    wheel = f"sc_collected_files/{environment.WHEELS}/scfake_helper-0.1.0-py3-none-any.whl"
    assert wheel in members
    test, = [name for name in members if name.endswith("/test_gcd.py")]
    assert f"{os.path.dirname(test)}/tbutil.py" in members
    assert members[f"{os.path.dirname(test)}/tbutil.py"] == b"import scfakeumi\n"
    assert not [name for name in members if name.startswith("sc_python")]


def test_a_compiled_local_package_is_refused_before_create(
        site, fake_v1, logged_in, offers_python_env):
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    _distribution(site, "scfakec", "1.0.0", archive=os.path.abspath("c.tar.gz"),
                  files={"_c.so": "\x7fELF"})
    project = cocotb_project("import scfakec\n")

    with pytest.raises(RemoteError, match="scfakec 1.0.0.*compiled file.*_c.so"):
        RemoteRun(project, logged_in)._preflight()
    assert not [c for c in fake_v1.calls if c.request.method == "POST"
                and c.request.url.endswith("/v1/jobs")]


def test_a_helper_holding_a_compiled_extension_is_refused(site, fake_v1, logged_in):
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    project = cocotb_project("import mine\n", {"mine/__init__.py": "", "mine/_c.so": "x"})

    with pytest.raises(RemoteError, match="compiled extension"):
        RemoteRun(project, logged_in)._python()


def test_packages_to_install_stop_before_create_where_the_server_installs_none(
        site, fake_v1, logged_in):
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    _distribution(site, "scfakeumi", "0.3.1")
    project = cocotb_project("import scfakeumi\n")

    with pytest.raises(RemoteError, match="needs scfakeumi==0.3.1.*python.env"):
        RemoteRun(project, logged_in)._check_python_env()
    assert not [c for c in fake_v1.calls if c.request.method == "POST"
                and c.request.url.endswith("/v1/jobs")]


def test_a_testbench_of_only_its_own_modules_needs_no_python_env(site, fake_v1, logged_in):
    '''Constraints alone install nothing: no `python_packages`, no
    `python.env`, and the helpers still travel.'''
    from siliconcompiler.remote.client.run import RemoteRun

    project = cocotb_project("import cocotb\nimport tbutil\n", {"tbutil.py": "X = 1\n"})

    member, built, helpers = RemoteRun(project, logged_in)._python()

    assert (member, built) == (None, {})
    assert [os.path.basename(path) for path in helpers] == ["tbutil.py"]


def test_a_flow_running_none_of_the_users_python_lists_nothing(
        site, gcd_nop_project, fake_v1, logged_in):
    from siliconcompiler.remote.client.run import RemoteRun

    assert RemoteRun(gcd_nop_project, logged_in)._python() == (None, {}, {})


class CannotSetUpHere(RunsATestbench):
    def setup(self):
        raise RuntimeError("cocotb is not installed")


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
        RemoteRun(project, logged_in)._python()


def test_one_setup_that_cannot_run_drops_no_other_nodes_python(
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

    member, _, _ = RemoteRun(project, logged_in)._python()

    assert member["requirements"] == ["scfakeumi==0.3.1"]


def test_a_python_entry_is_answered_with_a_repacked_wheel(site, fake_v1, logged_in):
    '''The server has no index offering it: the client repacks what is
    installed here, and sends only that.'''
    import responses

    from siliconcompiler.remote.client.run import RemoteRun

    _distribution(site, "scfake_private", "1.2.0")
    project = cocotb_project("import scfake_private\n")
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit",
                  {"id": "01J9-job", "state": "staging", "terminal": False}, status=202)

    RemoteRun(project, logged_in)._send_asked(
        "01J9-job", [{"kind": "python", "name": "scfake-private"}])

    members = _uploaded(fake_v1)
    wheel = f"sc_collected_files/{environment.WHEELS}/scfake_private-1.2.0-py3-none-any.whl"
    assert [name for name in members if members[name] is not None] == [wheel]
    grant = next(c for c in fake_v1.calls if "upload-grant" in c.request.path_url)
    put = next(c for c in fake_v1.calls if c.request.url == "https://storage.test/put")
    sent = put.request.body.read() if hasattr(put.request.body, "read") else put.request.body
    assert json.loads(grant.request.body)["digest"] == \
        f"sha256:{hashlib.sha256(sent).hexdigest()}"


def test_a_python_entry_asked_at_create_goes_in_the_first_archive(site, logged_in,
                                                                  tmp_path):
    '''Surface D306: an ask at create is answered in the first archive, the
    repacked wheel in the collection beside the manifest -- the moment before
    a follow-up, which is the other.'''
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.utils.paths import collectiondir

    _distribution(site, "scfake_private", "1.2.0")
    project = cocotb_project("import scfake_private\n")
    run = RemoteRun(project, logged_in)

    run._asked_rows = run._answer([{"kind": "python", "name": "scfake-private"}],
                                  collectiondir(project))
    run._pack(tmp_path / "first.tar.gz")

    with tarfile.open(tmp_path / "first.tar.gz") as tar:
        names = tar.getnames()
    assert f"sc_collected_files/{environment.WHEELS}/scfake_private-1.2.0-py3-none-any.whl" \
        in names
    assert f"{project.name}.pkg.json" in names


def test_a_compiled_package_asked_for_stops_and_cancels_the_job(site, fake_v1, logged_in):
    import responses

    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

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
    # No `authorized`, as sc-server's: a deployment that grants nothing gates
    # nothing, and `python.env` alone decides.
    (None, False, None),
    ([{"name": "python-env", "via": ["self"]}], False, None),
    ([], False, "is not granted python-env"),
    ([{"name": "python-env", "via": ["self"]}], True,
     "python-wheels to upload scfakeloose-3.0.0-py3-none-any.whl.*not granted python-wheels"),
    # Review row 29: each document in the way, with its signing link, or its
    # title from `terms` where the entry carries none.
    ([{"name": "python-env", "via": ["self"],
       "blocked_by": {"py-terms": {"url": "https://portal.test/terms"}}}], False,
     "holds python-env blocked on an agreement.*sign py-terms: https://portal.test/terms"),
    ([{"name": "python-env", "via": ["self"], "blocked_by": {"py-terms": {}}}], False,
     "blocked on an agreement.*sign The Python terms \\(no link is available"),
])
def test_a_capability_the_account_lacks_stops_the_run_before_create(
        site, fake_v1, logged_in, granted, wheel, stops):
    '''surface *Who may use it: three capabilities*: checked against
    `GET /v1/me`'s `authorized.capabilities` before create -- packages need
    `python-env`, wheels `python-wheels`.'''
    import responses

    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

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
    assert not [c for c in fake_v1.calls if c.request.method == "POST"
                and c.request.url.endswith("/v1/jobs")]


@pytest.mark.parametrize("resource,advice", [
    ("python-env", "Ask the deployment for the python-env grant. A job whose only "
                   "Python is its own modules needs none."),
    ("python-wheels", "Ask the deployment for the python-wheels grant, or publish the "
                      "package to one of its indexes."),
])
def test_a_capability_refused_at_create_says_which_and_what_to_do(
        site, fake_v1, logged_in, offers_python_env, resource, advice):
    '''sc-server grants nothing and never says this; a deployment that grants
    capabilities does, at create for `python-env` and on the job for
    `python-wheels` -- the same refusal either way.'''
    import responses

    from conftest import problem
    from siliconcompiler.remote.client.errors import ServerProblem, describe
    from siliconcompiler.remote.client.run import RemoteRun

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
    '''Once the job has staged: each listed version its images hold another
    of -- a release line's newest, where the listed one does not install or is
    yanked -- beside the one listed here. What matches is not said.'''
    import logging

    from siliconcompiler.remote.client.run import RemoteRun

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


def test_the_reuse_hash_carries_each_uploaded_wheels_digest(
        site, fake_v1, logged_in, capabilities):
    '''A wheel is built from whatever its source holds now, and the same
    version is often different code: two runs alike in all but the wheel's
    bytes are different jobs.'''
    import responses

    from siliconcompiler.remote.client.run import RemoteRun

    fake_v1.replace(responses.GET, "", dict(
        capabilities, features=capabilities["features"] + ["jobs.reuse", "python.env"]))
    _distribution(site, "scfakeloose", "3.0.0", archive=os.path.abspath("loose.tar.gz"),
                  files={"data.txt": "one\n"})
    project = cocotb_project("import scfakeloose\n")

    def sent(run):
        run._run_hash = lambda: "h-1"
        return run._reuse_hash()

    first = sent(RemoteRun(project, logged_in))
    again = sent(RemoteRun(project, logged_in))
    open(os.path.join(site, "scfakeloose", "data.txt"), "w").write("two\n")
    changed = sent(RemoteRun(project, logged_in))

    assert first == again != "h-1"
    assert changed != first
    assert sent(RemoteRun(cocotb_project("import cocotb\n"), logged_in)) == "h-1"
