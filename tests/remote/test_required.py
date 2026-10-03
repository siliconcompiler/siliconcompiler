import os

import pytest

from siliconcompiler import ASIC, Flowgraph, PDK, StdCellLibrary
from siliconcompiler.remote import owners
from siliconcompiler.tools.builtin.nop import NOPTask

from conftest import slug
from test_owners import (DATASHEET, GITHUB, Supply, account, collected_path, private,
                         resource, submit_project, two_sources)


# Only what the flow requires goes up (D129): the union of every running node's
# `require`, empty until setup runs, so worked out on a copy and carried.

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


def reading_mylib(gcd_design, tmp_path, pdk=None):
    '''A flow reading the datasheet, and not the quickstart, of a local library.'''
    lib = two_views(StdCellLibrary, "mylib", tmp_path / "lib")
    return reading(gcd_design, tmp_path, ("library", "mylib", *DATASHEET), pdk=pdk, libs=[lib])


def test_the_set_is_worked_out_by_setup_on_a_copy_and_carried_in_the_manifest(
        gcd_design, tmp_path):
    '''`require` is empty until setup runs, in the image; the run's own setup
    then declares the same keys, which `add_required_key` lists once.'''
    from siliconcompiler.scheduler.schedulernode import SchedulerNode

    project = reading_mylib(gcd_design, tmp_path)
    assert owners.required(project) is None

    manifest = carried(project)
    worked_out = owners.required(manifest)
    assert ("library", "mylib", *DATASHEET) in worked_out
    assert ("library", "mylib", *QUICKSTART) not in worked_out
    assert owners.required(project) is None             # the caller's project untouched
    node = SchedulerNode(manifest, "stepone", "0")
    with node.runtime():
        node.setup()
    assert manifest.get("tool", "builtin", "task", "nop", "require",
                        step="stepone", index="0") == ["library,mylib,package,doc,datasheet"]


def test_the_run_is_prepared_first_so_the_main_librarys_views_are_required(
        asic_heartbeat):
    '''`asic,asiclib` is filled from the main library by `_init_run()`;
    set up without it, no library's LEF is required at all.'''
    lib = asic_heartbeat.get_library(asic_heartbeat.get("asic", "mainlib"))

    worked_out = owners.required(carried(asic_heartbeat))

    assert any(("library", lib.name, "fileset", fileset, "file", "lef") in worked_out
               for fileset in lib.get("asic", "aprfileset"))
    # And a node the configuration removes reads nothing: nobody's LVS netlist.
    assert not any(key[-1] == "cdl" for key in worked_out)


def test_a_node_the_flow_does_not_run_reads_nothing(gcd_design, tmp_path):
    '''The union is over the nodes that RUN: `option,to` narrows it.'''
    project = reading_mylib(gcd_design, tmp_path)
    flow = project.get_flow()
    flow.node("steptwo", ReadsTask())
    flow.edge("stepone", "steptwo")
    project.set_flow(flow)
    project.set("tool", "builtin", "task", "nop", "var", "reads",
                ["library,mylib,package,doc,quickstart"], step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "var", "reads",
                ["library,mylib,package,doc,datasheet"], step="stepone", index="0")
    project.set("option", "to", "stepone")

    assert ("library", "mylib", *QUICKSTART) not in owners.required(carried(project))


def test_accounting_and_sources_see_only_what_the_flow_reads(gcd_design, tmp_path):
    '''A PDK holding nothing the flow reads is never sent for, never fetched.'''
    project = reading_mylib(gcd_design, tmp_path,
                            pdk=resource(PDK, "lambda", GITHUB, create=False))
    required = owners.required(carried(project))

    assert [item["keypath"][1] for item in owners.sources(project)] == ["lambda"]
    assert owners.sources(project, required) == []
    names = {entry.name for entry in account(project, "none", Supply(), required)}
    assert "lambda" not in names and "mylib" in names


@pytest.mark.parametrize("setup_runs", [True, False])
def test_only_what_the_flow_reads_goes_up_unless_its_setup_cannot_run_here(
        gcd_design, tmp_path, logged_in, monkeypatch, setup_runs):
    '''A library's views for ten tools used to all go up. A setup needing
    its image (cocotb's) leaves the set unknown: by owner alone, not failed.'''
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.utils.paths import collectiondir

    def cannot(project):
        raise RuntimeError("Cocotb is not installed; cannot run test.")

    if not setup_runs:
        monkeypatch.setattr(owners, "work_out", cannot)
    project = reading_mylib(gcd_design, tmp_path)

    run = RemoteRun(project, logged_in)
    if not setup_runs:
        assert run._needs() == (project, None)
    run._collect()

    def sent(key):
        return os.path.exists(os.path.join(collectiondir(project), collected_path(
            project, ("library", "mylib", *key))))
    assert sent(DATASHEET)
    assert sent(QUICKSTART) is not setup_runs


def test_a_private_file_beside_a_sent_one_stays_on_this_machine(
        gcd_design, tmp_path, logged_in):
    '''Per value: the local file of the parameter the flow reads goes up,
    and the private one beside it stays here -- the run is not stopped for it.'''
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.utils.paths import collectiondir

    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "other.pdf").write_text("private\n")
    pdk = two_sources(tmp_path, f"file+private://{tmp_path / 'secret'}")
    project = reading(gcd_design, tmp_path, ("library", "mixed", *DATASHEET), pdk=pdk)

    RemoteRun(project, logged_in)._collect()

    taken = [name for _, _, names in os.walk(collectiondir(project)) for name in names]
    assert "datasheet.pdf" in taken and "other.pdf" not in taken


@pytest.fixture
def dispatcher(server):
    from test_server_jobs import FakeDispatcher

    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.mark.parametrize("left_out,refused", [(DATASHEET, True), (QUICKSTART, False)])
def test_only_a_required_file_left_out_is_refused_before_dispatch(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path,
        left_out, refused):
    '''One the flow reads is `missing_member` before anything runs, not a
    node failing on it; one it does not read may be left out.'''
    project = carried(reading_mylib(gcd_design, tmp_path, pdk=PDK("lambda")))

    _, response = submit_project(
        server_client, key, token, job_archive, project,
        left_out=collected_path(project, ("library", "mylib", *left_out)))

    if refused:
        assert response.status_code == 422
        assert (slug(response), response.get_json()["reason"]) == \
            ("archive-rejected", "missing_member")
        assert "library,mylib,package,doc,datasheet" in response.get_json()["detail"]
        assert not dispatcher.submitted
    else:
        assert response.status_code == 202, response.get_json()
        assert dispatcher.submitted


def test_a_source_nothing_in_the_flow_reads_is_never_fetched(
        server, server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    from test_server_sources_flow import LAMBDA, fake_fetch, wait_for
    from siliconcompiler.remote.server.staging.sources import Permanent

    fake_fetch(server, fail=Permanent("fetched a source nothing reads"))
    project = carried(reading_mylib(gcd_design, tmp_path,
                                    pdk=resource(PDK, "lambda", LAMBDA, create=False)))

    _, response = submit_project(server_client, key, token, job_archive, project)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)


def test_a_required_file_missing_from_the_servers_copy_is_resource_unavailable(
        server, server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''One the server should have supplied, and cannot.'''
    root = tmp_path / "operator-copy"
    root.mkdir()                                     # and no datasheet in it
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"secret": {"secret": str(root)}}}
    project = carried(reading(gcd_design, tmp_path, ("library", "secret", *DATASHEET),
                              pdk=private(PDK, "secret", tmp_path / "client-copy")))

    _, response = submit_project(server_client, key, token, job_archive, project)

    assert (response.status_code, slug(response)) == (422, "resource-unavailable")
    assert "not in this server's copy" in response.get_json()["detail"]
    assert not dispatcher.submitted


def test_a_follow_up_carries_only_the_required_values_of_what_was_asked(
        server, server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''A dataroot in `upload_sources` selects the required values under it --
    never the whole repository.'''
    from test_server_sources_flow import LAMBDA, fake_fetch, read, send, wait_for
    from siliconcompiler.remote.server.staging.sources import Permanent

    fake_fetch(server, fail=Permanent("the source answered 404"))
    pdk = resource(PDK, "lambda", LAMBDA, create=False)
    with pdk.active_dataroot("lambda"):
        pdk.set(*QUICKSTART, "quickstart.pdf")
    project = carried(reading(gcd_design, tmp_path, ("library", "lambda", *DATASHEET),
                              pdk=pdk))

    job, response = submit_project(server_client, key, token, job_archive, project)
    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")

    unread = collected_path(project, ("library", "lambda", *QUICKSTART))
    refused = send(server_client, key, token, job["id"],
                   {f"sc_collected_files/{unread}": b"not asked for\n"})
    assert refused.get_json()["reason"] == "unrequested_member"
