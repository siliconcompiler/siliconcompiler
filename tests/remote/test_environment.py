import json
import os
import zipfile

from pathlib import Path

import pytest

from conftest import outcome

from siliconcompiler import Flowgraph
from siliconcompiler.remote import environment
from siliconcompiler.remote.server.jobs import pythonenv
from siliconcompiler.tools.builtin.nop import NOPTask


# A job's Python packages (surface *A node's own Python packages, built while
# staging*): the create body's `python_packages`, held to one grammar at both
# ends, and the wheels under `sc_collected_files/python/`, held to what an
# upload may carry -- then installed while staging, from the deployment's own
# indexes, where the job's nodes that run the user's Python find them.


def make_wheel(where, name, version, requires=(), files=None, tag="py3-none-any",
               wheel_tags=None, purelib=True):
    '''A wheel, as small as pip will take, with what a test needs wrong in
    it. Returns its path.'''
    escaped = name.replace("-", "_")
    path = os.path.join(str(where), f"{escaped}-{version}-{tag}.whl")
    info = f"{escaped}-{version}.dist-info"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n" + \
        "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
    members = dict(files if files is not None else {f"{escaped}/__init__.py": "VALUE = 1\n"})
    members[f"{info}/METADATA"] = metadata
    members[f"{info}/WHEEL"] = (
        "Wheel-Version: 1.0\nGenerator: test\n"
        f"Root-Is-Purelib: {'true' if purelib else 'false'}\n"
        + "".join(f"Tag: {one}\n" for one in (wheel_tags or [tag])))
    members[f"{info}/RECORD"] = "".join(f"{member},,\n" for member in
                                        [*members, f"{info}/RECORD"])
    with zipfile.ZipFile(path, "w") as archive:
        for member, body in members.items():
            archive.writestr(member, body)
    return path


###########################
# The lists' grammar
###########################

def test_what_the_lists_take():
    packages = environment.parse({"requirements": ["numpy==1.26.4", "pyuvm==3.0.0"],
                                  "constraints": ["scapy==2.5.0", "cocotbext-eth==0.1.28"]})

    assert [str(pin) for pin in packages.requirements] == ["numpy==1.26.4", "pyuvm==3.0.0"]
    assert [str(pin) for pin in packages.constraints] == \
        ["scapy==2.5.0", "cocotbext-eth==0.1.28"]
    assert packages.names() == {"numpy", "pyuvm", "scapy", "cocotbext-eth"}
    assert environment.parse({}) == environment.Packages()
    # Every PEP 440 form in its canonical spelling.
    for version in ("2!1.0", "1.0rc1", "1.0.post2", "1.0.dev3", "2.1.0+cpu.1"):
        assert environment.parse_entry(f"x=={version}").version == version


@pytest.mark.parametrize("entry", [
    "numpy>=1.26",                              # a range
    "numpy==1.26.*",                            # a wildcard
    "numpy[extra]==1.26.4",                     # extras
    "numpy==1.26.4; python_version>'3'",        # a marker
    "numpy == 1.26.4",                          # whitespace
    "numpy===1.26.4",                           # arbitrary equality
    "numpy==v1.26.4",                           # not canonical
    "numpy==1.0-rc1",                           # not canonical
    "git+https://github.com/x/y",               # a VCS URL
    "./local",                                  # a path
    "-e .",                                     # an option
    "--index-url https://pkgs.example.com/",    # an index
    "",
    "numpy",
    7,
])
def test_everything_else_is_refused_naming_the_entry(entry):
    with pytest.raises(environment.PackagesError) as refused:
        environment.parse({"requirements": ["ok==1.0", entry]})

    assert refused.value.entry is not None


def test_each_name_once_across_both_lists_as_pep_503_sees_it():
    with pytest.raises(environment.PackagesError, match="named twice") as refused:
        environment.parse({"requirements": ["Foo_Bar==1.0"], "constraints": ["foo-bar==2.0"]})

    assert refused.value.entry == "foo-bar==2.0"


def test_the_bounds():
    with pytest.raises(environment.PackagesError, match="1001 entries"):
        environment.parse({"constraints": [f"p{n}==1.0" for n in range(1001)]})
    long = "x" * 100
    with pytest.raises(environment.PackagesError, match="bytes"):
        environment.parse({"constraints": [f"{long}{n}==1.0" for n in range(700)]})
    with pytest.raises(environment.PackagesError, match="no member 'extras'"):
        environment.parse({"requirements": [], "extras": []})
    with pytest.raises(environment.PackagesError, match="is an object"):
        environment.parse(["numpy==1.0"])


def test_the_builder_writes_its_own_files_from_what_parsed():
    '''🔴 Nothing the job wrote is handed to pip: the names are the
    canonical ones, one per line.'''
    packages = environment.parse({"requirements": ["PyUVM==3.0.0"]})

    text = environment.render(packages.requirements, header="written here")

    assert text == "# written here\npyuvm==3.0.0\n"


###########################
# A wheel, held to what an upload may carry
###########################

def test_a_pure_wheel_is_taken(tmp_path):
    path = make_wheel(tmp_path, "scfake-helper", "0.1.0")

    wheel = environment.check_wheel(path)
    assert wheel[:3] == ("scfake-helper", "0.1.0", os.path.basename(path))
    # What it holds, for the extraction limits: the module and its dist-info.
    assert wheel.members == 4 and wheel.expanded > 0
    assert environment.wheel_name(path) == "scfake-helper"


@pytest.mark.parametrize("change,why", [
    (dict(tag="cp312-cp312-linux_x86_64"), "only a pure wheel"),
    (dict(files={"scfake/_c.so": "\x7fELF"}), "compiled file"),
    (dict(files={"scfake/_c.cpython-312-darwin.DYLIB": "x"}), "compiled file"),
    (dict(files={"../escape.py": ""}), "does not stay inside"),
    (dict(files={"/abs.py": ""}), "does not stay inside"),
    (dict(purelib=False), "Root-Is-Purelib"),
    (dict(wheel_tags=["py3-none-manylinux1_x86_64"]), "tags it for a platform"),
    # surface D292: nothing that runs by itself, and no dependency by URL.
    (dict(files={"scfake_hook.pth": "import os\n"}), "a .pth file"),
    (dict(files={"scfake/nested.pth": "import os\n"}), "a .pth file"),
    (dict(files={"sitecustomize.py": "print('hello')\n"}), "runs in any Python"),
    (dict(files={"usercustomize.py": "print('hello')\n"}), "runs in any Python"),
    (dict(files={"scfake-1.0.data/scripts/run": "#!/bin/sh\n"}), "installs outside"),
    (dict(requires=["scfake-bits @ https://example.test/bits.whl"]), "dependency by URL"),
    (dict(requires=["scfake-bits @ file:///home/someone/bits"]), "dependency by URL"),
])
def test_a_wheel_that_is_not_pure_or_is_malformed_is_refused(tmp_path, change, why):
    path = make_wheel(tmp_path, "scfake", "1.0", **change)

    with pytest.raises(environment.WheelError, match=why):
        environment.check_wheel(path)


def test_a_wheel_must_say_inside_what_its_name_says(tmp_path):
    path = make_wheel(tmp_path, "scfake", "1.0")
    os.rename(path, tmp_path / "other-1.0-py3-none-any.whl")

    with pytest.raises(environment.WheelError, match="names another"):
        environment.check_wheel(tmp_path / "other-1.0-py3-none-any.whl")

    (tmp_path / "junk-1.0-py3-none-any.whl").write_bytes(b"not a zip")
    with pytest.raises(environment.WheelError, match="not a zip"):
        environment.check_wheel(tmp_path / "junk-1.0-py3-none-any.whl")

    with pytest.raises(environment.WheelError, match="not named as a wheel"):
        environment.check_wheel(tmp_path / "scfake.zip")


def test_a_wheel_whose_own_module_is_called_sitecustomize_inside_a_package_is_taken(
        tmp_path):
    '''Only a TOP-LEVEL sitecustomize runs by itself; one inside a package is
    that package's module.'''
    path = make_wheel(tmp_path, "scfake", "1.0",
                      files={"scfake/sitecustomize.py": "VALUE = 1\n"})

    assert environment.check_wheel(path).name == "scfake"


def test_a_link_in_a_wheel_is_refused(tmp_path):
    path = make_wheel(tmp_path, "scfake", "1.0")
    with zipfile.ZipFile(path, "a") as archive:
        info = zipfile.ZipInfo("scfake/link")
        info.external_attr = 0o120777 << 16
        archive.writestr(info, "/etc/passwd")

    with pytest.raises(environment.WheelError, match="link"):
        environment.check_wheel(path)


###########################
# At create
###########################

pytest.importorskip("flask", reason="the server extra is not installed")


def slug(response):
    return (response.get_json().get("type") or "").rsplit("/", 1)[-1]


def offers_python_env(server):
    server.config["SC_CONFIG"]._values["features"] = \
        server.config["SC_CONFIG"]["features"] + ["python.env"]
    return server


def test_a_lists_entry_outside_the_grammar_is_refused_at_create(
        server, server_client, key, token):
    '''`400 invalid-request`, naming the entry: a client bug.'''
    from test_server_jobs import create

    offers_python_env(server)
    response = create(server_client, key, token,
                      python_packages={"requirements": ["numpy>=1.26"]})

    assert response.status_code == 400
    assert slug(response) == "invalid-request"
    assert "numpy>=1.26" in response.get_json()["detail"]


def test_packages_where_the_deployment_installs_none_are_refused_at_create(
        server, server_client, key, token):
    from test_server_jobs import create

    assert "python.env" not in server.config["SC_CONFIG"]["features"]
    response = create(server_client, key, token,
                      python_packages={"requirements": ["numpy==1.26.4"]})

    assert response.status_code == 501
    assert (slug(response), response.get_json()["feature"]) == \
        ("feature-unsupported", "python.env")


def test_the_lists_are_kept_on_the_job_as_the_grammar_took_them(
        server, server_client, key, token):
    from test_server_jobs import create

    offers_python_env(server)
    member = {"requirements": ["numpy==1.26.4"], "constraints": ["scapy==2.5.0"]}
    job = create(server_client, key, token, python_packages=member,
                 idempotency_key="k-1").get_json()

    stored = server.config["SC_STORE"].one(
        "SELECT python_packages FROM jobs WHERE id = ?", (job["id"],))
    assert json.loads(stored["python_packages"]) == member
    assert "python_packages" not in job          # the builder's input, never echoed

    # The same key with other packages is another request.
    again = create(server_client, key, token, python_packages={"requirements": []},
                   idempotency_key="k-1")
    assert slug(again) == "idempotency-key-reuse"


###########################
# While staging
###########################

@pytest.fixture
def dispatcher(server):
    from test_server_jobs import FakeDispatcher

    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def with_wheels(job_archive, project, *wheels):
    return job_archive(project, extra={
        f"{environment.wheels_path()}/{os.path.basename(path)}": open(path, "rb").read()
        for path in wheels})


def submitted(server_client, key, token, archive, **body):
    from test_server_jobs import stage, submit

    path, digest, size = archive
    job = stage(server_client, key, token, path, size, **body)
    return outcome(server_client, key, token,
                   submit(server_client, key, token, job["id"], digest, size))


@pytest.fixture
def installed(monkeypatch, tmp_path):
    '''Host mode's install while staging, without pip: what it was asked
    for, and a site of its own for each -- or, where ``absent`` is set, the
    packages no index has.'''
    from siliconcompiler.remote.server.packages import envinstall

    asked = []

    def install(packages, wheels, root, logger, constrain=(), indexes=(), **_):
        asked.append(([str(pin) for pin in packages.requirements],
                      [str(pin) for pin in packages.constraints],
                      [os.path.basename(path) for path in wheels], list(indexes)))
        if install.absent:
            raise envinstall.InstallFailed({"returncode": 1, "absent": install.absent.pop(0)})
        site = tmp_path / "sites" / str(len(asked))
        site.mkdir(parents=True)
        return str(site), {"installed": [["numpy", "1.26.4"]], "substituted": {},
                           "ignored": {"packaging": ["1.0", "25.0"]}}

    install.absent = []
    install.asked = asked
    monkeypatch.setattr(envinstall, "install", install)
    return install


def test_a_wheel_where_the_deployment_installs_none_is_refused(
        server, server_client, key, token, job_archive, python_project, tmp_path):
    response = submitted(server_client, key, token, with_wheels(
        job_archive, python_project, make_wheel(tmp_path, "scfake-helper", "0.1.0")))

    assert response.status_code == 422
    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "python_package")


@pytest.mark.parametrize("wheels,body,why", [
    ([("scfake", "1.0", {"tag": "cp312-cp312-linux_x86_64"})], {}, "only a pure wheel"),
    ([("scfake", "1.0", {"files": {"scfake/_c.so": "x"}})], {}, "compiled"),
    # 🔴 A distribution travels one way: as a wheel, or in the lists.
    ([("scfake", "1.0", {})],
     {"python_packages": {"requirements": ["scfake==1.0"]}}, "also lists"),
    ([("scfake", "1.0", {})],
     {"python_packages": {"requirements": ["numpy==1.26.4"],
                          "constraints": ["scfake==0.9"]}}, "also lists"),
    ([("scfake", "1.0", {}), ("scfake", "1.1", {})], {}, "both wheels for scfake"),
    # surface D292, named by the file in the wheel.
    ([("scfake", "1.0", {"files": {"scfake_hook.pth": "import os\n"}})], {},
     "scfake_hook.pth"),
    ([("scfake", "1.0", {"requires": ["bits @ https://example.test/bits.whl"]})], {},
     "dependency by URL"),
])
def test_a_wheel_that_is_impure_or_overlaps_is_refused(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        wheels, body, why):
    offers_python_env(server)
    made = [make_wheel(tmp_path, name, version, **change)
            for name, version, change in wheels]

    response = submitted(server_client, key, token,
                         with_wheels(job_archive, python_project, *made), **body)

    assert response.status_code == 422, response.get_json()
    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "python_package")
    assert why in response.get_json()["detail"]


def test_a_wheels_own_members_are_held_to_the_extraction_limits(
        server, server_client, key, token, job_archive, python_project, tmp_path):
    '''A wheel's members are held as any member is, counted together with the
    archive's own (surface D292): a small wheel that expands past what the
    archive may is refused as the archive would be, naming it.'''
    import tarfile

    offers_python_env(server)
    big = make_wheel(tmp_path, "scfake", "1.0", files={
        "scfake/__init__.py": "", "scfake/data.txt": "0" * (4 << 20)})
    archive = with_wheels(job_archive, python_project, big)
    with tarfile.open(archive[0]) as tar:
        own = sum(member.size for member in tar.getmembers())
    server.config["SC_CONFIG"].limits["max_archive_expanded_bytes"] = own + (1 << 20)

    response = submitted(server_client, key, token, archive)

    assert response.status_code == 422, response.get_json()
    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "expanded_bytes")
    assert "scfake-1.0-py3-none-any.whl" in response.get_json()["detail"]


def test_a_wheel_for_what_requested_versions_python_names_is_refused(
        server, server_client, key, token, job_archive, python_project, tmp_path):
    '''The image holds it, and a second copy would be the one the tool loads.'''
    from importlib.metadata import version

    offers_python_env(server)
    held = version("packaging")
    response = submitted(
        server_client, key, token,
        with_wheels(job_archive, python_project, make_wheel(tmp_path, "packaging", held)),
        requested_versions={"python": {"packaging": [f"=={held}"]}})

    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "python_package")
    assert "requested_versions.python" in response.get_json()["detail"]


def test_the_old_python_tree_is_not_where_anything_goes(
        server, server_client, key, token, job_archive, python_project):
    '''`sc_python/` left the first archive's allowlist: the server writes it.'''
    offers_python_env(server)
    response = submitted(server_client, key, token, job_archive(
        python_project, extra={"sc_python/nodes/stepone/0/requirements.txt": b"x==1.0\n"}))

    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "unrequested_member")


def test_the_lists_and_the_wheels_are_installed_once_while_staging(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        installed, dispatcher):
    '''From the deployment's own indexes; linked where a node running the
    user's Python finds it; and what it did is in the job-level log.'''
    offers_python_env(server)
    helper = make_wheel(tmp_path, "scfake-helper", "0.1.0")

    response = submitted(
        server_client, key, token, with_wheels(job_archive, python_project, helper),
        python_packages={"requirements": ["numpy==1.26.4"], "constraints": ["scapy==2.5.0"]})

    assert response.status_code == 202, response.get_json()
    assert installed.asked == [(["numpy==1.26.4"], ["scapy==2.5.0"],
                                [os.path.basename(helper)], ["https://pypi.org/simple/"])]
    assert dispatcher.submitted

    job = response.get_json()
    jobs = server.config["SC_JOBS"]
    tree = jobs.job_root(job["owner"]["id"], job["id"]) / "gcd" / "job0"
    assert (tree / environment.site_path()).is_symlink()
    # What the install added is in the job's `staging` record (surface D295).
    from siliconcompiler.remote.server.outputs import record
    log = (jobs.job_root(job["owner"]["id"], job["id"]) / record.STAGING_LOG).read_text()
    assert "installed numpy==1.26.4" in log
    assert "packaging 25.0 (listed 1.0)" in log


@pytest.mark.parametrize("flow,body", [
    # No node runs the user's Python: nothing is installed for it.
    ("nop", {"python_packages": {"requirements": ["numpy==1.26.4"]}}),
    # Constraints alone install nothing.
    ("python", {"python_packages": {"constraints": ["scapy==2.5.0"]}}),
])
def test_nothing_is_installed_where_nothing_would_use_it(
        server, server_client, key, token, job_archive, nop_project, python_project,
        installed, dispatcher, flow, body):
    offers_python_env(server)
    project = python_project if flow == "python" else nop_project
    if flow == "nop":
        plain = Flowgraph("nopflow2")
        plain.node("stepone", NOPTask())
        nop_project.set_flow(plain)

    response = submitted(server_client, key, token, job_archive(project), **body)

    assert response.status_code == 202, response.get_json()
    assert installed.asked == []
    assert dispatcher.submitted


def test_a_package_no_index_has_is_sent_back_and_answered_with_its_wheel(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        installed, dispatcher):
    '''🔴 Asked for by name, `{"kind": "python"}`; the wheel that answers
    replaces the listed entry, and is the one wheel that may overlap the
    lists. Anything else in the follow-up is not what was asked for.'''
    from conftest import call
    from test_server_sources_flow import send

    offers_python_env(server)
    installed.absent = [["scfake-private"]]
    member = {"requirements": ["numpy==1.26.4", "scfake-private==1.2.0"],
              "constraints": ["scapy==2.5.0"]}

    response = submitted(server_client, key, token, job_archive(python_project),
                         python_packages=member)
    job = call(server_client, key, "GET", f"/v1/jobs/{response.get_json()['id']}",
               token).get_json()
    assert job["state"] == "awaiting_input", job
    assert job["upload_sources"] == [{"kind": "python", "name": "scfake-private"}]
    assert not dispatcher.submitted

    # A wheel nobody asked for is refused.
    other = make_wheel(tmp_path, "scfake-other", "1.0")
    refused = send(server_client, key, token, job["id"], {
        f"{environment.wheels_path()}/{os.path.basename(other)}": open(other, "rb").read()})
    assert refused.get_json()["reason"] == "unrequested_member"


def test_the_wheel_that_answers_is_installed_in_place_of_its_entry(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        installed, dispatcher):
    from conftest import call
    from test_server_sources_flow import send

    offers_python_env(server)
    installed.absent = [["scfake-private"]]
    member = {"requirements": ["numpy==1.26.4", "scfake-private==1.2.0"]}
    response = submitted(server_client, key, token, job_archive(python_project),
                         python_packages=member)
    job_id = response.get_json()["id"]

    private = make_wheel(tmp_path, "scfake-private", "1.2.0")
    answered = send(server_client, key, token, job_id, {
        f"{environment.wheels_path()}/{os.path.basename(private)}": open(private, "rb").read()})

    assert answered.status_code == 202, answered.get_json()
    job = call(server_client, key, "GET", f"/v1/jobs/{job_id}", token).get_json()
    assert job["state"] != "rejected", job
    assert installed.asked[-1] == (["numpy==1.26.4"], [], [os.path.basename(private)],
                                   ["https://pypi.org/simple/"])
    assert dispatcher.submitted


def test_a_package_asked_for_at_create_is_answered_in_the_first_archive(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        installed, dispatcher, monkeypatch):
    '''🔴 Surface D306: the wheel exception covers an ask at create as well
    as a job sent back. The wheel in the first archive replaces its listed
    entry, and is not refused as an overlap. This server's create asks only
    for dataroots, so the ask is made for it here.'''
    from conftest import call
    from siliconcompiler.remote.server.jobs import JobService

    offers_python_env(server)
    real = JobService._look_up
    monkeypatch.setattr(JobService, "_look_up", lambda self, declared: real(
        self, declared) + [{"kind": "python", "name": "scfake-private"}])
    member = {"requirements": ["numpy==1.26.4", "scfake-private==1.2.0"]}
    private = make_wheel(tmp_path, "scfake-private", "1.2.0")

    response = submitted(server_client, key, token,
                         with_wheels(job_archive, python_project, private),
                         python_packages=member, sources=[])

    assert response.status_code == 202, response.get_json()
    job = call(server_client, key, "GET", f"/v1/jobs/{response.get_json()['id']}",
               token).get_json()
    assert job["state"] != "rejected", job
    assert installed.asked[-1][:3] == (["numpy==1.26.4"], [], [os.path.basename(private)])
    assert dispatcher.submitted


def test_an_unasked_wheel_beside_its_listed_entry_is_still_an_overlap(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        installed, dispatcher):
    '''The exception is for what was asked: the same wheel, unasked, is a
    distribution travelling two ways.'''
    offers_python_env(server)
    member = {"requirements": ["numpy==1.26.4", "scfake-private==1.2.0"]}
    private = make_wheel(tmp_path, "scfake-private", "1.2.0")

    response = submitted(server_client, key, token,
                         with_wheels(job_archive, python_project, private),
                         python_packages=member, sources=[])

    assert (slug(response), response.get_json()["reason"]) == \
        ("archive-rejected", "python_package")


def test_the_wheel_that_answers_is_at_its_entrys_version(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        installed, dispatcher):
    '''🔴 It replaces the entry, so it is at the entry's version (surface
    D286): another is `python_package`, naming both.'''
    from test_server_sources_flow import send

    offers_python_env(server)
    installed.absent = [["scfake-private"]]
    response = submitted(server_client, key, token, job_archive(python_project),
                         python_packages={"requirements": ["scfake-private==1.2.0"]})
    job_id = response.get_json()["id"]

    other = make_wheel(tmp_path, "scfake-private", "1.3.0")
    refused = send(server_client, key, token, job_id, {
        f"{environment.wheels_path()}/{os.path.basename(other)}": open(other, "rb").read()})

    assert (slug(refused), refused.get_json()["reason"]) == \
        ("archive-rejected", "python_package")
    assert "1.3.0" in refused.get_json()["detail"] and "1.2.0" in refused.get_json()["detail"]
    assert not dispatcher.submitted


@pytest.mark.parametrize("result,expected", [
    ({"returncode": 1, "python": "cpython-test", "version": "3", "platform": "test-platform",
      "unresolved": ["numpy==1.26.4"], "network": False,
      "tail": "ERROR: No matching distribution found for numpy==1.*"}, "uninstallable"),
    ({"returncode": 1, "python": "cpython-test", "platform": "test-platform",
      "unresolved": [], "network": True, "tail": "NewConnectionError"}, "staging-failed"),
])
def test_a_package_that_will_not_install_rejects_the_job_before_any_node_runs(
        server, server_client, key, token, job_archive, python_project, dispatcher,
        monkeypatch, result, expected):
    '''🔴 Host mode installs while staging, so a package that will not install
    is `rejected`, `software-unavailable`, `uninstallable`, naming the package
    and the target -- not a failed run. An index that does not answer is this
    server's failure: `failed`, `staging-failed`.'''
    from conftest import call
    from siliconcompiler.remote.server.packages import envinstall

    def install(*args, **kwargs):
        raise envinstall.InstallFailed(result)

    monkeypatch.setattr(envinstall, "install", install)
    offers_python_env(server)

    from test_server_jobs import stage, submit

    path, digest, size = job_archive(python_project)
    created = stage(server_client, key, token, path, size,
                    python_packages={"requirements": ["numpy==1.26.4"]})
    submit(server_client, key, token, created["id"], digest, size)
    job = call(server_client, key, "GET", f"/v1/jobs/{created['id']}", token).get_json()

    error = job["error"]
    if expected == "uninstallable":
        assert job["state"] == "rejected"
        assert (error["type"].rsplit("/", 1)[-1], error["reason"]) == \
            ("software-unavailable", "uninstallable")
        assert {key: error["unresolved"][0][key] for key in ("kind", "name")} == \
            {"kind": "package", "name": "numpy"}
        assert "cpython-test" in error["detail"] and "test-platform" in error["detail"]
    else:
        assert job["state"] == "failed"
        assert error["type"].endswith("/staging-failed")
    assert not dispatcher.submitted


###########################
# End to end, pip for real, over an index on disk
###########################

def simple_index(where, *wheels):
    '''A PEP 503 index on disk over some wheels, as a file: URL.'''
    root = where / "simple"
    for path in wheels:
        project = environment.wheel_name(path)
        (root / project).mkdir(parents=True, exist_ok=True)
        os.replace(path, root / project / os.path.basename(path))
        (root / project / "index.html").write_text("".join(
            f'<a href="{name}">{name}</a>\n' for name in sorted(os.listdir(root / project))
            if name.endswith(".whl")))
    root.mkdir(exist_ok=True)
    return root.as_uri() + "/"


def test_a_job_with_packages_and_a_wheel_runs_to_the_end(
        server, server_client, key, token, job_archive, python_project, tmp_path,
        monkeypatch):
    '''🔴 One job through every step with pip for real: a package the index has
    and one it does not; the job sent back for that one, and answered with its
    wheel; the lists and the wheels installed while staging into the user's own
    cache; linked where the node's task finds them; dispatched here; and run to
    the end.'''
    import time

    from conftest import call
    from test_server_sources_flow import send

    pytest.importorskip("pip")
    # The run's own process imports the node's task class by name.
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(
        [os.path.dirname(__file__), *os.environ.get("PYTHONPATH", "").split(os.pathsep)]))
    offers_python_env(server)
    made = tmp_path / "made"
    made.mkdir()
    index = simple_index(tmp_path, make_wheel(made, "scfake-bits", "1.2.0"))
    server.config["SC_CONFIG"]._values["package_indexes"] = [index]

    response = submitted(
        server_client, key, token, with_wheels(job_archive, python_project, make_wheel(
            made, "scfake-helper", "0.1.0", requires=["scfake-bits>=1"])),
        python_packages={"requirements": ["scfake-bits==1.2.0", "scfake-private==0.3.0"]})
    job_id = response.get_json()["id"]

    def settled(*states):
        deadline = time.monotonic() + 120
        while True:
            job = call(server_client, key, "GET", f"/v1/jobs/{job_id}", token).get_json()
            if job["state"] in states or job["terminal"] or time.monotonic() > deadline:
                return job
            time.sleep(0.2)

    job = settled("awaiting_input")
    assert job["upload_sources"] == [{"kind": "python", "name": "scfake-private"}], job

    private = make_wheel(made, "scfake-private", "0.3.0")
    assert send(server_client, key, token, job_id, {
        f"{environment.wheels_path()}/{os.path.basename(private)}":
            open(private, "rb").read()}).status_code == 202

    job = settled("completed")
    assert job["state"] == "completed", job

    jobs = server.config["SC_JOBS"]
    tree = jobs.job_root(job["owner"]["id"], job_id) / "gcd" / "job0"
    site = tree / environment.site_path()
    assert site.is_symlink()
    # 🔴 The environment of its key, never one in the user's cache that two
    # of their jobs could write at once.
    assert site.resolve().parent == (Path(server.config["SC_DATADIR"])
                                     / pythonenv.ENVIRONMENTS).resolve()
    assert sorted(entry for entry in os.listdir(site) if not entry.endswith("-info")) == \
        ["scfake_bits", "scfake_helper", "scfake_private"]


###########################
# The tool's path
###########################

def test_the_packages_go_on_the_path_of_a_node_running_the_users_python_only(
        python_project):
    '''🔴 Never on SiliconCompiler's own path, and never on a node whose task
    runs none of the user's Python.'''
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.utils.paths import jobdir

    site = os.path.join(jobdir(python_project), environment.site_path())
    os.makedirs(site)

    def path(step):
        node = SchedulerNode(python_project, step, "0")
        with node.runtime():
            return node.task.get_runtime_environmental_variables().get(
                "PYTHONPATH", "").split(os.pathsep)

    assert path("stepone")[0] == site
    assert site not in path("steptwo")


###########################
# The deployment
###########################

def test_the_deployment_does_not_advertise_what_it_cannot_build(tmp_path):
    '''No builder: where nodes run in containers there is nothing to install
    a job's packages with.'''
    from siliconcompiler.remote.server.config import Config

    (tmp_path / "config.json").write_text(json.dumps(
        {"features": ["python.env"], "containers": True}))
    with pytest.raises(ValueError, match="python.env"):
        Config.load(tmp_path)


def test_bare_slurm_with_no_builder_offers_no_python_env(tmp_path):
    from siliconcompiler.remote.server.app import create_app

    (tmp_path / "config.json").write_text(
        json.dumps({"features": ["logs.stream", "python.env"]}))
    with pytest.raises(ValueError, match="python.env"):
        create_app(tmp_path, cluster="slurm")


@pytest.mark.parametrize("containers,available", [(False, []), (True, [])])
def test_a_python_name_nothing_here_holds_is_refused_at_create(
        server, server_client, key, token, containers, available):
    '''🔴 A server never ignores a listed name: host mode answers from its
    own Python, and where nodes run in containers, from the live images.'''
    from conftest import call

    server.config["SC_CONFIG"]._values["containers"] = containers
    response = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job0",
        "descriptor": {"requested_versions": {"python": {"scnosuchdistribution": ["==1.0"]}}}})

    assert response.status_code == 422, response.get_json()
    body = response.get_json()
    assert slug(response) == "software-unavailable"
    assert body["unresolved"] == [{"kind": "python", "name": "scnosuchdistribution",
                                   "requirement": ["==1.0"], "available": available}]


def test_host_mode_answers_from_its_own_python(server, server_client, key, token):
    from importlib.metadata import version

    from conftest import call

    ok = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job0",
        "descriptor": {"requested_versions": {
            "python": {"packaging": [f"=={version('packaging')}"]}}}})
    assert ok.status_code == 201, ok.get_json()

    other = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job1",
        "descriptor": {"requested_versions": {"python": {"packaging": ["==0.0.1"]}}}})
    assert other.status_code == 422
    assert other.get_json()["unresolved"][0]["available"] == [version("packaging")]
