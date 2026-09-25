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
# 🔴 A `$`-rooted path is the client's to expand, and it goes up (D112)
###########################

def test_a_dollar_rooted_pdk_is_local_and_uploaded(project, tmp_path, monkeypatch):
    '''Reverses D109: the server never expands a variable, so the client does
    -- with its own environment and `option,env` -- and uploads what it finds.'''
    root = tmp_path / "site-pdk"
    root.mkdir()
    (root / "datasheet.pdf").write_text("the datasheet\n")
    monkeypatch.setenv("FOUNDRY_ROOT", str(root))
    project.set_pdk(resource(PDK, "foundry", "$FOUNDRY_ROOT", create=False))

    assert decide(project, ("library", "foundry", *DATASHEET)) == (owners.LOCAL, True)


###########################
# Private: supplied by name, never uploaded
###########################

def private(cls, name, root):
    obj = cls(name)
    obj.set_dataroot(name, f"file+private://{root}")
    with obj.active_dataroot(name):
        obj.set(*DATASHEET, "datasheet.pdf")
    return obj


def test_a_private_pdk_is_never_uploaded(project, tmp_path):
    '''Even though it is local -- private wins over the owner table.'''
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "datasheet.pdf").write_text("x")
    project.set_pdk(private(PDK, "secret", tmp_path / "secret"))

    assert decide(project, ("library", "secret", *DATASHEET)) == (owners.PRIVATE, False)


def test_the_marker_is_tested_in_one_place():
    '''Its spelling is open; switching is an edit to `is_private` alone.'''
    from siliconcompiler.package import FileResolver, PrivateFileResolver

    assert owners.is_private(PrivateFileResolver("x", None, "file+private:///a"))
    assert not owners.is_private(FileResolver("x", None, "/a"))


###########################
# What the client says it expects the server to supply
###########################

def test_sources_names_what_is_not_uploaded_and_strips_credentials(project, tmp_path):
    project.set_pdk(resource(PDK, "lambda",
                             "https://user:token@github.com/siliconcompiler/x/archive/",
                             create=False))
    project.add_asiclib(private(StdCellLibrary, "secretlib", tmp_path))

    listed = {(item["kind"], item["name"]): item for item in owners.sources(project)}

    remote = listed[("pdk", "lambda")]
    assert remote["source"] == "https://github.com/siliconcompiler/x/archive/"
    assert remote["ref"] == "v1" and remote["private"] is False

    hidden = listed[("library", "secretlib")]
    # 🔴 A private dataroot's path is never sent.
    assert hidden["private"] is True and "source" not in hidden
    assert ("design", "gcd") not in listed


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
            select=lambda key, dataroot, resolvers, path: owners.uploads(
                project, key, dataroot, resolvers, path))

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
# The server's half: every file uploaded or supplied by identity
###########################

class Supply:
    '''A server, as `account` asks it.'''

    def __init__(self, packages=(), private=None, held=None, allowed=()):
        self.packages, self.private = set(packages), private or {}
        self.held_roots, self.allowed = held or {}, list(allowed)

    def package(self, module):
        return module in self.packages

    def private_root(self, name, dataroot):
        return self.private.get((name, dataroot))

    def held(self, source, ref):
        return self.held_roots.get((source, ref))

    def allowlisted(self, source, ref):
        return any(str(source).startswith(prefix) for prefix in self.allowed)


def status(project, name, supply, collection="none"):
    for entry in owners.account(project, collection, supply):
        if entry.name == name:
            return entry
    raise AssertionError(f"{name} not accounted for")


def test_a_library_rooted_at_etc_is_never_read_from_the_host(project):
    '''🔴 The live hole (D112). A manifest roots a library at `/etc`, leaves it
    out of the archive -- and the file IS there on this machine. It used to be
    looked for, found and supplied: anyone reading the host's files into a job.
    Now it is asked of the client, and the path is never looked at.'''
    lib = StdCellLibrary("hostfiles")
    lib.set_dataroot("hostfiles", "/etc")
    with lib.active_dataroot("hostfiles"):
        lib.set(*DATASHEET, "passwd")
    project.add_asiclib(lib)

    assert status(project, "hostfiles", Supply()).status == owners.ASK


def test_an_uploaded_file_is_accounted_as_uploaded(project, tmp_path):
    project.set_pdk(resource(PDK, "mine", tmp_path / "pdk"))
    collection = tmp_path / "sc_collected_files"
    collection.mkdir()
    value = first(project, ("library", "mine", *DATASHEET))
    (collection / value.get_hashed_filename()).write_text("uploaded\n")

    assert status(project, "mine", Supply(), collection).status == owners.UPLOADED


def test_a_remote_source_is_fetched_only_from_the_allowlist(project):
    source = "https://github.com/siliconcompiler/x/archive/"
    project.set_pdk(resource(PDK, "lambda", source, create=False))

    listed = status(project, "lambda", Supply(allowed=["https://github.com/siliconcompiler/"]))
    assert (listed.status, listed.source, listed.ref) == (owners.FETCH, source, "v1")

    # Not on the list: not refused -- asked of the client, which sends it.
    assert status(project, "lambda", Supply()).status == owners.ASK


def test_a_held_source_is_supplied_from_the_servers_copy(project, tmp_path):
    source = "https://github.com/siliconcompiler/x/archive/"
    project.set_pdk(resource(PDK, "lambda", source, create=False))
    held = tmp_path / "held"
    held.mkdir()

    entry = status(project, "lambda", Supply(held={(source, "v1"): str(held)}))
    assert (entry.status, entry.root) == (owners.SUPPLIED, str(held))


def test_a_private_dataroot_is_supplied_by_name_or_not_at_all(project, tmp_path):
    root = tmp_path / "operator-copy"
    root.mkdir()
    project.set_pdk(private(PDK, "secret", "/wherever/the/client/had/it"))

    mapped = status(project, "secret", Supply(private={("secret", "secret"): str(root)}))
    assert (mapped.status, mapped.root) == (owners.SUPPLIED, str(root))
    assert status(project, "secret", Supply()).status == owners.UNAVAILABLE


def test_a_private_design_is_refused(project, tmp_path):
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("mine", f"file+private://{tmp_path}")
    with design.active_dataroot("mine"), design.active_fileset("rtl"):
        design.add_file("top.v")

    entries = [entry for entry in owners.account(
        project, "none", Supply(private={("gcd", "mine"): str(tmp_path)}))
        if entry.dataroot == "mine"]
    assert [entry.status for entry in entries] == [owners.UNAVAILABLE]


def test_a_path_escaping_a_supplied_root_is_refused(project, tmp_path):
    root = tmp_path / "operator-copy"
    root.mkdir()
    pdk = private(PDK, "secret", "/anywhere")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "../../etc/passwd")
    project.set_pdk(pdk)

    entry = status(project, "secret", Supply(private={("secret", "secret"): str(root)}))
    assert entry.status == owners.UNAVAILABLE


def test_confined_follows_symlinks_and_refuses_the_way_out(tmp_path):
    root = tmp_path / "root"
    (root / "inside").mkdir(parents=True)
    (root / "inside" / "ok.lef").write_text("x")
    (root / "escape").symlink_to("/etc")

    assert owners.confined(root, "inside/ok.lef") == \
        str((root / "inside" / "ok.lef").resolve())
    assert owners.confined(root, "escape/passwd") is None
    assert owners.confined(root, "../outside") is None
    assert owners.confined(root, "/etc/passwd") is None


def test_an_installed_package_is_supplied_where_the_server_has_it(project):
    project.set_pdk(resource(PDK, "pkg", "python://some_pdk_package", create=False))

    assert status(project, "pkg", Supply(packages=["some_pdk_package"])).status == \
        owners.SUPPLIED
    assert status(project, "pkg", Supply()).status == owners.ASK


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


def _nop_asic(gcd_design, tmp_path, pdk):
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask

    project = ASIC(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    project.set_flow(flow)
    project.set_pdk(pdk)
    project.option.set_nodashboard(True)
    project.option.set_jobname("job0")
    project.option.set_builddir(str(tmp_path / "build"))
    return project


def _upload_without(project, archive, tmp_path, left_out):
    '''The archive with one collected file taken out of it.'''
    import hashlib
    import tarfile

    stripped = tmp_path / "stripped.tar.gz"
    with tarfile.open(archive) as source, tarfile.open(stripped, "w:gz") as out:
        for member in source.getmembers():
            if left_out not in member.name:
                out.addfile(member, source.extractfile(member) if member.isfile() else None)
    body = stripped.read_bytes()
    return str(stripped), "sha256:" + hashlib.sha256(body).hexdigest(), len(body)


def test_a_local_pdk_left_out_is_asked_for_not_supplied_from_the_host(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''🔴 At submit: the file is on this machine, and the job is asked for it
    rather than supplied it.'''
    from conftest import call
    from test_server_jobs import stage, submit

    project = _nop_asic(gcd_design, tmp_path, resource(PDK, "mine", tmp_path / "pdk"))
    archive, _, _ = job_archive(project)
    hashed = first(project, ("library", "mine", *DATASHEET)).get_hashed_filename()
    archive, digest, size = _upload_without(project, archive, tmp_path, hashed)

    job = stage(server_client, key, token, archive, size)
    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 202
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "awaiting_input"
    assert read["upload_sources"] == [{"kind": "pdk", "name": "mine", "dataroot": "mine"}]
    assert not dispatcher.submitted


def test_a_private_pdk_the_server_has_no_copy_of_is_refused(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    from conftest import call, slug
    from test_server_jobs import stage, submit

    project = _nop_asic(gcd_design, tmp_path, private(PDK, "secret", tmp_path))
    archive, digest, size = job_archive(project)
    job = stage(server_client, key, token, archive, size)
    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 422
    assert slug(response) == "resource-unavailable"
    assert (response.get_json()["resource_kind"], response.get_json()["resource"]) == \
        ("pdk", "secret")
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "rejected"


def test_a_mapped_private_pdk_runs_and_the_manifest_says_whose_copy(
        server, server_client, key, token, job_archive, dispatcher, gcd_design,
        tmp_path):
    '''The operator's copy, confined -- and the manifest the run loads points
    each dataroot at the copy it resolves to (D111).'''
    import json
    from test_server_jobs import stage, submit

    root = tmp_path / "operator-copy"
    root.mkdir()
    (root / "datasheet.pdf").write_text("x")
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "secret": {"secret": str(root)}}

    (tmp_path / "client-copy").mkdir()
    (tmp_path / "client-copy" / "datasheet.pdf").write_text("x")
    project = _nop_asic(gcd_design, tmp_path,
                        private(PDK, "secret", tmp_path / "client-copy"))
    archive, digest, size = job_archive(project)
    job = stage(server_client, key, token, archive, size)
    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 202, response.get_json()
    text = open(dispatcher.submitted[0][2]).read()
    manifest = json.loads(text)
    pointed = json.dumps(manifest["library"]["secret"]["dataroot"]["secret"]["path"])
    assert str(root) in pointed
    assert str(tmp_path / "client-copy") not in text
    assert "sc_collected_files" in json.dumps(manifest["library"]["gcd"]["dataroot"])
