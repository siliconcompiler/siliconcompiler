import os

import pytest

from siliconcompiler import ASIC, Flowgraph, PDK, StdCellLibrary
from siliconcompiler.remote import owners
from siliconcompiler.tools.builtin.nop import NOPTask

from conftest import outcome, slug
from test_owners import DATASHEET, _upload_without, collected_path, first, private


# Only what the flow requires goes up (D129). The owner table says whether a
# value MAY go in the archive; the flow says whether it is NEEDED -- the union of
# every running node's `require`, which is empty until setup runs, so the client
# works it out on a copy and carries it in the manifest.

QUICKSTART = ("package", "doc", "quickstart")


class ReadsTask(NOPTask):
    '''A task that requires the keys `var,reads` names -- what a driver's setup
    does with `add_required_key`.'''

    def __init__(self):
        super().__init__()
        self.add_parameter("reads", "[str]", "keypaths this task reads, comma-joined")

    def setup(self):
        super().setup()
        for key in self.get("var", "reads"):
            self.add_required_key(*key.split(","))


def two_views(cls, name, root):
    '''A local resource with two files, of which a flow may read one.'''
    obj = cls(name)
    obj.set_dataroot(name, str(root))
    os.makedirs(root, exist_ok=True)
    with obj.active_dataroot(name):
        for key, file in ((DATASHEET, "datasheet.pdf"), (QUICKSTART, "quickstart.pdf")):
            obj.set(*key, file)
            with open(os.path.join(root, file), "w") as f:
                f.write(f"{file}\n")
    return obj


def reading(gcd_design, tmp_path, *keys, pdk=None, libs=()):
    '''A one-node flow whose task reads ``keys`` and nothing else.'''
    project = ASIC(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("readflow")
    flow.node("stepone", ReadsTask())
    project.set_flow(flow)
    if pdk:
        project.set_pdk(pdk)
    for lib in libs:
        project.add_asiclib(lib)
    project.set("tool", "builtin", "task", "nop", "var", "reads",
                [",".join(key) for key in keys])
    project.option.set_nodashboard(True)
    project.option.set_jobname("job0")
    project.option.set_builddir(str(tmp_path / "build"))
    return project


def carried(project):
    '''The manifest a client uploads: its `require` worked out and carried.'''
    return owners.with_required(project, owners.work_out(project).required)


###########################
# The set
###########################

def test_the_set_is_worked_out_by_setup_on_a_copy(gcd_design, tmp_path):
    '''🔴 `require` is empty until setup runs, and a remote run's setup runs in
    the image -- so read before it, every file would be dropped.'''
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET), libs=[lib])

    assert owners.required(project) is None

    worked_out = owners.required(carried(project))
    assert ("library", "mylib", *DATASHEET) in worked_out
    assert ("library", "mylib", *QUICKSTART) not in worked_out
    # The caller's project is never touched.
    assert owners.required(project) is None


def test_the_run_is_prepared_first_so_the_main_librarys_views_are_required(
        asic_heartbeat):
    '''⚠️ `asic,asiclib` is filled from the main library by `_init_run()`;
    set up without it, no library's LEF is required at all.'''
    lib = asic_heartbeat.get_library(asic_heartbeat.get("asic", "mainlib"))

    worked_out = owners.required(carried(asic_heartbeat))

    assert any(("library", lib.name, "fileset", fileset, "file", "lef") in worked_out
               for fileset in lib.get("asic", "aprfileset"))
    # And a node the configuration removes reads nothing: nobody's LVS netlist.
    assert not any(key[-1] == "cdl" for key in worked_out)


def test_a_node_the_flow_does_not_run_reads_nothing(gcd_design, tmp_path):
    '''The union is over the nodes that RUN: `option,to` narrows it.'''
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET), libs=[lib])
    flow = project.get_flow()
    flow.node("steptwo", ReadsTask())
    flow.edge("stepone", "steptwo")
    project.set_flow(flow)
    project.set("tool", "builtin", "task", "nop", "var", "reads",
                ["library,mylib,package,doc,quickstart"], step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "var", "reads",
                ["library,mylib,package,doc,datasheet"], step="stepone", index="0")
    project.set("option", "to", "stepone")

    worked_out = owners.required(carried(project))

    assert ("library", "mylib", *QUICKSTART) not in worked_out


def test_accounting_and_sources_see_only_what_the_flow_reads(gcd_design, tmp_path):
    source = "https://github.com/siliconcompiler/x/archive/"
    pdk = PDK("lambda")
    pdk.set_dataroot("lambda", source, tag="v1")
    with pdk.active_dataroot("lambda"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET),
                      pdk=pdk, libs=[lib])
    required = owners.required(carried(project))

    # The PDK holds nothing the flow reads: never sent for, never fetched.
    assert [item["name"] for item in owners.sources(project)] == ["lambda"]
    assert owners.sources(project, required) == []

    from test_owners import Supply
    names = {entry.name for entry in owners.account(project, "none", Supply(), required)}
    assert "lambda" not in names and "mylib" in names


###########################
# The client
###########################

def test_only_what_the_flow_reads_goes_up(gcd_design, tmp_path, logged_in):
    '''A local library with views for ten tools used to upload all ten.'''
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.utils.paths import collectiondir

    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET), libs=[lib])

    RemoteRun(project, logged_in)._collect()

    collected = collectiondir(project)
    assert os.path.exists(os.path.join(
        collected, collected_path(first(project, ("library", "mylib", *DATASHEET)))))
    assert not os.path.exists(os.path.join(
        collected, collected_path(first(project, ("library", "mylib", *QUICKSTART)))))


def test_a_private_file_beside_a_sent_one_stops_the_run_here(
        gcd_design, tmp_path, logged_in):
    '''🔴 A parameter goes up whole, so one holding a private file beside a
    local one is refused on this machine, naming it -- before anything is
    collected.'''
    from siliconcompiler.remote.client.errors import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.utils.paths import collectiondir
    from test_owners import two_sources

    (tmp_path / "secret").mkdir()
    pdk = two_sources(tmp_path, f"file+private://{tmp_path / 'secret'}")
    project = reading(gcd_design, tmp_path, ("library", "mixed", *DATASHEET), pdk=pdk)

    with pytest.raises(RemoteError, match=r"library,mixed,package,doc,datasheet"):
        RemoteRun(project, logged_in)._collect()
    assert not os.path.exists(collectiondir(project))


def test_a_setup_that_cannot_run_here_uploads_by_owner_alone(
        gcd_design, tmp_path, logged_in, monkeypatch):
    '''⚠️ A task whose setup needs what only its image has -- cocotb's needs
    cocotb -- leaves the set unknown, and a remote run must not fail for it.'''
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.utils.paths import collectiondir

    def cannot(project):
        raise RuntimeError("Cocotb is not installed; cannot run test.")

    monkeypatch.setattr(owners, "work_out", cannot)
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET), libs=[lib])

    run = RemoteRun(project, logged_in)
    assert run._needs() == (project, None)

    run._collect()
    assert os.path.exists(os.path.join(
        collectiondir(project),
        collected_path(first(project, ("library", "mylib", *QUICKSTART)))))


def test_the_manifest_carries_the_set_and_the_run_adds_nothing_twice(
        gcd_design, tmp_path):
    '''The server reads the set from the manifest it is sent; the run's own
    setup then declares the same keys, which `add_required_key` lists once.'''
    from siliconcompiler.scheduler.schedulernode import SchedulerNode

    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    manifest = carried(reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET),
                               libs=[lib]))

    node = SchedulerNode(manifest, "stepone", "0")
    with node.runtime():
        node.setup()

    assert manifest.get("tool", "builtin", "task", "nop", "require",
                        step="stepone", index="0") == ["library,mylib,package,doc,datasheet"]


###########################
# The server
###########################

@pytest.fixture
def dispatcher(server):
    pytest.importorskip("flask", reason="the server extra is not installed")
    from test_server_jobs import FakeDispatcher

    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def submitted(server_client, key, token, job_archive, project, tmp_path, left_out=None):
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive(project)
    if left_out:
        archive, digest, size = _upload_without(project, archive, tmp_path, left_out)
    job = stage(server_client, key, token, archive, size)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


def test_a_required_file_the_client_should_have_sent_is_refused_before_dispatch(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''🔴 A local library's file the flow reads, left out: `missing_member`,
    before anything runs -- instead of a node failing on it.'''
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = carried(reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET),
                              pdk=PDK("lambda"), libs=[lib]))
    hashed = collected_path(first(project, ("library", "mylib", *DATASHEET)))

    job, response = submitted(server_client, key, token, job_archive, project, tmp_path,
                              left_out=hashed)

    assert response.status_code == 422
    assert slug(response) == "archive-rejected"
    assert response.get_json()["reason"] == "missing_member"
    assert "library,mylib,package,doc,datasheet" in response.get_json()["detail"]
    assert not dispatcher.submitted


def test_a_file_the_flow_does_not_read_may_be_left_out(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = carried(reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET),
                              pdk=PDK("lambda"), libs=[lib]))
    hashed = collected_path(first(project, ("library", "mylib", *QUICKSTART)))

    job, response = submitted(server_client, key, token, job_archive, project, tmp_path,
                              left_out=hashed)

    assert response.status_code == 202, response.get_json()
    assert dispatcher.submitted


def test_a_source_nothing_in_the_flow_reads_is_never_fetched(
        server, server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    from test_server_sources_flow import LAMBDA, fake_fetch, wait_for
    from siliconcompiler.remote.server.staging.sources import Permanent

    fake_fetch(server, fail=Permanent("fetched a source nothing reads"))
    pdk = PDK("lambda")
    pdk.set_dataroot("lambda", LAMBDA, tag="v1")
    with pdk.active_dataroot("lambda"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    project = carried(reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET),
                              pdk=pdk, libs=[lib]))

    job, response = submitted(server_client, key, token, job_archive, project, tmp_path)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)


def test_a_required_file_missing_from_the_servers_copy_is_resource_unavailable(
        server, server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''🔴 One the server should have supplied, and cannot.'''
    root = tmp_path / "operator-copy"
    root.mkdir()                                     # and no datasheet in it
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "secret": {"secret": str(root)}}
    project = carried(reading(gcd_design, tmp_path, ("library", "secret", *DATASHEET),
                              pdk=private(PDK, "secret", tmp_path / "client-copy")))

    job, response = submitted(server_client, key, token, job_archive, project, tmp_path)

    assert response.status_code == 422
    assert slug(response) == "resource-unavailable"
    assert "not in this server's copy" in response.get_json()["detail"]
    assert not dispatcher.submitted


def test_a_follow_up_carries_only_the_required_values_of_what_was_asked(
        server, server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''A dataroot in `upload_sources` selects the required values under it --
    never the whole repository.'''
    from test_server_sources_flow import LAMBDA, fake_fetch, read, send, wait_for
    from siliconcompiler.remote.server.staging.sources import Permanent

    fake_fetch(server, fail=Permanent("the source answered 404"))
    pdk = PDK("lambda")
    pdk.set_dataroot("lambda", LAMBDA, tag="v1")
    with pdk.active_dataroot("lambda"):
        pdk.set(*DATASHEET, "datasheet.pdf")
        pdk.set(*QUICKSTART, "quickstart.pdf")
    project = carried(reading(gcd_design, tmp_path, ("library", "lambda", *DATASHEET),
                              pdk=pdk))

    job, response = submitted(server_client, key, token, job_archive, project, tmp_path)
    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")

    unread = collected_path(first(project, ("library", "lambda", *QUICKSTART)))
    refused = send(server_client, key, token, job["id"],
                   {f"sc_collected_files/{unread}": b"not asked for\n"})
    assert refused.get_json()["reason"] == "unrequested_member"
