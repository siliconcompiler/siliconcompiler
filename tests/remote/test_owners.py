import os

import pytest

from siliconcompiler import ASIC, PDK, StdCellLibrary
from siliconcompiler.remote import owners


# What goes in a remote run's archive, decided by what owns each file and where
# its dataroot says it comes from -- and the server's half, which refuses a flow
# that needs a resource it does not hold and did not receive.

DATASHEET = ("package", "doc", "datasheet")


def resource(cls, name, root, file="datasheet.pdf", create=True):
    obj = cls(name)
    remote = str(root).startswith(("https://", "git"))
    # A remote source needs a reference to name what it fetches.
    obj.set_dataroot(name, str(root), tag="v1" if remote else None)
    with obj.active_dataroot(name):
        obj.set(*DATASHEET, file)
    if create:
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, file), "w") as f:
            f.write("the datasheet\n")
    return obj


@pytest.fixture
def project(gcd_design):
    return ASIC(gcd_design)


def first(project, key):
    '''The first value of a parameter, out of the list it may be held in.'''
    value = project.get(*key, field=None).getvalues(return_values=False)[0][0]
    return value.values[0] if hasattr(value, "values") else value


def decide(project, key):
    '''What `collect`'s selector is asked about one value.'''
    value = first(project, key)
    resolvers = project.get(*key[:-1], field="schema")._find_files_dataroot_resolvers(True)
    dataroot = value.get(field="dataroot")
    return (owners.source(resolvers, dataroot),
            owners.uploads(project, key, dataroot, resolvers))


###########################
# Who owns it
###########################

def test_every_owner_is_told_apart(project, tmp_path):
    '''⚠️ PDK and StdCellLibrary subclass Design, so they are tested first --
    the other way round every PDK is the user's design and always uploaded.'''
    project.set_pdk(resource(PDK, "mypdk", tmp_path / "pdk"))
    project.set_mainlib(resource(StdCellLibrary, "mylib", tmp_path / "lib"))

    assert owners.owner(project, ("library", "mypdk", *DATASHEET)) == ("pdk", "mypdk")
    assert owners.owner(project, ("library", "mylib", *DATASHEET)) == ("library", "mylib")
    assert owners.owner(project, ("library", "gcd", "fileset", "rtl", "file", "verilog")) \
        == (owners.DESIGN, "gcd")
    assert owners.owner(project, ("tool", "openroad", "task", "x", "script")) == \
        ("tool", "openroad")
    assert owners.owner(project, ("option", "builddir")) == (owners.PROJECT, None)


def test_the_design_always_goes_up_whatever_its_source(project):
    assert decide(project, ("library", "gcd", "fileset", "rtl", "file", "verilog"))[1]


def test_the_credentials_file_never_goes_up(project, tmp_path):
    '''🔴 It is a path parameter the user sets, and it is this machine's key.'''
    creds = tmp_path / "credentials"
    creds.write_text("{}")
    project.option.set_credentials(str(creds))

    assert not decide(project, ("option", "credentials"))[1]


###########################
# 🔴 The trap: the SOURCE, never where the file is now
###########################

def test_a_remote_pdk_is_not_uploaded_even_though_its_files_are_on_disk(project):
    '''The failure that is silent. A lambdapdk PDK is fetched into the cache on
    first use, so every file it names IS on local disk -- judged by location,
    every PDK would go up in every job.'''
    project.set_pdk(resource(PDK, "remote", "https://example.test/pdk.tar.gz",
                             create=False))

    assert decide(project, ("library", "remote", *DATASHEET)) == (owners.REMOTE, False)


def test_a_local_pdk_is_uploaded(project, tmp_path):
    project.set_pdk(resource(PDK, "local", tmp_path / "pdk"))

    assert decide(project, ("library", "local", *DATASHEET)) == (owners.LOCAL, True)


def test_an_installed_package_is_not_uploaded_and_an_editable_one_is(
        project, monkeypatch):
    from siliconcompiler.package import PythonPathResolver

    project.set_pdk(resource(PDK, "pkg", "python://some_pdk_package", create=False))
    key = ("library", "pkg", *DATASHEET)

    monkeypatch.setattr(PythonPathResolver, "is_python_module_editable",
                        staticmethod(lambda module: False))
    assert decide(project, key) == (owners.INSTALLED, False)

    monkeypatch.setattr(PythonPathResolver, "is_python_module_editable",
                        staticmethod(lambda module: module == "some_pdk_package"))
    assert decide(project, key) == (owners.EDITABLE, True)


def test_a_dataroot_naming_another_is_judged_by_that_one(project):
    pdk = PDK("chained")
    pdk.set_dataroot("real", "https://example.test/pdk.tar.gz", tag="v1")
    pdk.set_dataroot("alias", "dataroot://real")
    with pdk.active_dataroot("alias"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(pdk)

    assert decide(project, ("library", "chained", *DATASHEET)) == (owners.REMOTE, False)


###########################
# collect(), told what to take
###########################

def test_collect_takes_what_the_owner_rule_selects_and_no_flag_is_touched(
        project, tmp_path):
    from siliconcompiler.utils.curation import collect
    from siliconcompiler.utils.paths import collectiondir

    project.option.set_builddir(str(tmp_path / "build"))
    project.set_pdk(resource(PDK, "local", tmp_path / "pdk"))
    project.add_asiclib(resource(StdCellLibrary, "remote",
                                 "https://example.test/lib.tar.gz", create=False))

    collect(project, verbose=False,
            select=lambda key, dataroot, resolvers: owners.uploads(
                project, key, dataroot, resolvers))

    taken = os.listdir(collectiondir(project))
    assert any(name.startswith("gcd") and name.endswith(".v") for name in taken)
    assert any(name.startswith("datasheet") for name in taken)
    # Remote: not fetched, not collected.
    assert len([name for name in taken if name.startswith("datasheet")]) == 1

    # 🔴 The caller's project is not rewritten to get there.
    assert not project.get("library", "local", *DATASHEET, field="copy")


def test_without_a_selector_collect_still_reads_copy(project, tmp_path):
    '''`sc-issue` and every other caller: unchanged.'''
    from siliconcompiler.utils.curation import collect
    from siliconcompiler.utils.paths import collectiondir

    project.option.set_builddir(str(tmp_path / "build"))
    project.set_pdk(resource(PDK, "local", tmp_path / "pdk"))

    collect(project, verbose=False)

    assert not any(name.startswith("datasheet")
                   for name in os.listdir(collectiondir(project)))


###########################
# The server's half: held, uploaded, or refused
###########################

def test_a_local_resource_not_uploaded_and_not_here_is_not_held(project, tmp_path):
    project.set_pdk(resource(PDK, "mine", tmp_path / "pdk"))
    os.remove(tmp_path / "pdk" / "datasheet.pdf")      # only its author had it

    assert owners.holding(project, "mine", tmp_path / "none") == (False, False)


def test_an_uploaded_copy_is_held_and_says_it_was_uploaded(project, tmp_path):
    project.set_pdk(resource(PDK, "mine", tmp_path / "pdk"))
    value = first(project, ("library", "mine", *DATASHEET))

    collection = tmp_path / "sc_collected_files"
    collection.mkdir()
    (collection / value.get_hashed_filename()).write_text("uploaded\n")
    os.remove(tmp_path / "pdk" / "datasheet.pdf")

    assert owners.holding(project, "mine", collection) == (True, True)


def test_a_remote_resource_is_held_because_the_server_fetches_it(project, tmp_path):
    project.set_pdk(resource(PDK, "lambda", "https://example.test/pdk.tar.gz",
                             create=False))

    assert owners.holding(project, "lambda", tmp_path) == (True, False)


def test_an_installed_package_the_server_cannot_import_is_not_held(project, tmp_path):
    project.set_pdk(resource(PDK, "pkg", "python://no_such_pdk_package_here",
                             create=False))

    assert owners.holding(project, "pkg", tmp_path)[0] is False


###########################
# ... and at submit
###########################

@pytest.fixture
def dispatcher(server):
    pytest.importorskip("flask", reason="the server extra is not installed")
    from test_server_jobs import FakeDispatcher

    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def private_pdk_project(gcd_design, tmp_path):
    '''An ASIC run on a PDK whose files only its author has.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask

    project = ASIC(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    project.set_flow(flow)
    project.set_pdk(resource(PDK, "private", tmp_path / "private-pdk"))
    project.option.set_nodashboard(True)
    project.option.set_jobname("job0")
    project.option.set_builddir(str(tmp_path / "build"))
    return project


def _submit(server_client, key, token, job_archive, project, extra=None):
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive(project, extra=extra)
    job = stage(server_client, key, token, archive, size)
    return job, submit(server_client, key, token, job["id"], digest, size)


def test_a_pdk_neither_held_nor_uploaded_is_refused_at_submit(
        server_client, key, token, job_archive, private_pdk_project, dispatcher,
        tmp_path):
    '''🔴 At re-derivation, not on the first node with the cluster paid for.
    ⚠️ `resource-unavailable`, not `resource-unresolved`: the server knows
    WHICH, and does not have it.'''
    from conftest import call, slug

    os.remove(tmp_path / "private-pdk" / "datasheet.pdf")

    job, response = _submit(server_client, key, token, job_archive, private_pdk_project)

    assert response.status_code == 422
    assert slug(response) == "resource-unavailable"
    assert response.get_json()["resource_kind"] == "pdk"
    assert response.get_json()["resource"] == "private"
    assert not dispatcher.submitted

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "rejected"


def test_the_same_pdk_uploaded_is_accepted(server_client, key, token, job_archive,
                                           private_pdk_project, dispatcher, tmp_path):
    value = first(private_pdk_project, ("library", "private", *DATASHEET))
    uploaded = {f"sc_collected_files/{value.get_hashed_filename()}": b"the datasheet\n"}
    os.remove(tmp_path / "private-pdk" / "datasheet.pdf")

    _, response = _submit(server_client, key, token, job_archive,
                          private_pdk_project, extra=uploaded)

    assert response.status_code == 202, response.get_json()
    assert dispatcher.submitted
