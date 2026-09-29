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


def first(project, key, n=0):
    '''The first value of a parameter, out of the list it may be held in.'''
    value = project.get(*key, field=None).getvalues(return_values=False)[0][0]
    return value.values[n] if hasattr(value, "values") else value


def collected_path(value):
    '''Where `collect` puts one value, under the collection directory.'''
    from siliconcompiler.schema.parametervalue import PathNodeValue

    return PathNodeValue.generate_hashed_collection_path(
        value.get(), value.get(field="dataroot"))


def decide_value(project, key, n):
    '''`decide`, for the ``n``-th value of the parameter.'''
    value = first(project, key, n)
    resolvers = project.get(*key[:-1], field="schema")._find_files_dataroot_resolvers(True)
    dataroot = value.get(field="dataroot")
    return (owners.source(resolvers, dataroot),
            owners.uploads(project, key, dataroot, resolvers))


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


@pytest.mark.parametrize("scheme", [
    "file+private", "git+private", "git+https+private", "git+ssh+private",
    "ssh+private", "http+private", "https+private"])
def test_every_private_scheme_is_private_before_any_other_rule(project, tmp_path, scheme):
    '''🔴 The marker is a `+private` suffix on any scheme (surface D274), read
    through `Resolver.is_private` before every other source rule: never
    uploaded, and supplied by name with no source or ref.'''
    local = scheme == "file+private"
    source = f"{scheme}://{tmp_path / 'secret'}" if local else f"{scheme}://host/secret.git"
    pdk = PDK("secret")
    pdk.set_dataroot("secret", source, tag=None if local else "v1")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(pdk)

    assert decide(project, ("library", "secret", *DATASHEET)) == (owners.PRIVATE, False)
    entry, = [item for item in owners.sources(project) if item["name"] == "secret"]
    assert entry["private"] is True and "source" not in entry and "ref" not in entry


def test_a_private_pdk_is_never_uploaded(project, tmp_path):
    '''Even though it is local -- private wins over the owner table.'''
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "datasheet.pdf").write_text("x")
    project.set_pdk(private(PDK, "secret", tmp_path / "secret"))

    assert decide(project, ("library", "secret", *DATASHEET)) == (owners.PRIVATE, False)


def test_the_marker_is_tested_in_one_place():
    '''A `+private` scheme, on a local path or a fetched source alike.'''
    from siliconcompiler.package import FileResolver
    from siliconcompiler.package.git import GitResolver

    assert owners.is_private(FileResolver("x", None, "file+private:///a"))
    assert owners.is_private(GitResolver("x", None, "git+ssh+private://host/a.git", "v1"))
    assert not owners.is_private(FileResolver("x", None, "/a"))
    assert not owners.is_private(GitResolver("x", None, "git+ssh://host/a.git", "v1"))


###########################
# What the client says it expects the server to supply
###########################

def test_sources_names_what_is_not_uploaded_and_strips_credentials(project, tmp_path):
    project.set_pdk(resource(PDK, "lambda",
                             "https://user:token@github.com/siliconcompiler/x/archive/",
                             create=False))
    project.add_asiclib(private(StdCellLibrary, "secretlib", tmp_path))

    listed = {(item["name"], item["dataroot"]): item for item in owners.sources(project)}
    # By owner and dataroot, and no kind: the server finds it from the name.
    assert not any("kind" in item for item in listed.values())

    remote = listed[("lambda", "lambda")]
    assert remote["source"] == "https://github.com/siliconcompiler/x/archive/"
    assert remote["ref"] == "v1" and remote["private"] is False

    hidden = listed[("secretlib", "secretlib")]
    # 🔴 A private dataroot's path is never sent.
    assert hidden["private"] is True and "source" not in hidden
    assert not any(name == "gcd" for name, _ in listed)


###########################
# collect(), told what to take: a parameter at a time
###########################

def uploaded_by_owner(project):
    '''What a remote run hands `collect`, by the owner rule alone.'''
    return owners.collection_keys(project, lambda one: owners.uploads(
        project, one.key, one.dataroot, one.resolvers, one.value.get()))


def collected_names(project):
    from siliconcompiler.utils.paths import collectiondir

    return [name for _, _, names in os.walk(collectiondir(project)) for name in names]


def test_collect_takes_what_the_owner_rule_selects_and_no_flag_is_touched(
        project, tmp_path):
    from siliconcompiler.utils.curation import collect

    project.option.set_builddir(str(tmp_path / "build"))
    project.set_pdk(resource(PDK, "local", tmp_path / "pdk"))
    project.add_asiclib(resource(StdCellLibrary, "remote",
                                 "https://example.test/lib.tar.gz", create=False))

    collect(project, keys=uploaded_by_owner(project), verbose=False)

    taken = collected_names(project)
    assert "gcd.v" in taken
    # Remote: not fetched, not collected.
    assert taken.count("datasheet.pdf") == 1

    # 🔴 The caller's project is not rewritten to get there.
    assert not project.get("library", "local", *DATASHEET, field="copy")


def two_sources(tmp_path, second, *, create=True):
    '''A PDK whose one datasheet parameter holds a local file and one from
    ``second``.'''
    pdk = PDK("mixed")
    pdk.set_dataroot("here", str(tmp_path / "pdk"))
    remote = second.startswith(("https://", "git"))
    pdk.set_dataroot("there", second, tag="v1" if remote else None)
    with pdk.active_dataroot("here"):
        pdk.add(*DATASHEET, "datasheet.pdf")
    with pdk.active_dataroot("there"):
        pdk.add(*DATASHEET, "other.pdf")
    os.makedirs(tmp_path / "pdk", exist_ok=True)
    (tmp_path / "pdk" / "datasheet.pdf").write_text("the datasheet\n")
    return pdk


def test_a_parameter_goes_up_whole(project, tmp_path):
    '''⚠️ `collect` takes a parameter's values together, so a value the
    server could supply goes with a local one beside it.'''
    project.set_pdk(two_sources(tmp_path, "https://example.test/pdk.tar.gz"))
    key = ("library", "mixed", *DATASHEET)
    assert [decide_value(project, key, n)[0] for n in (0, 1)] == [owners.LOCAL, owners.REMOTE]

    assert [where[0] for where in uploaded_by_owner(project)
            if where[0][:2] == ("library", "mixed")] == [key]


def test_a_private_value_beside_an_uploaded_one_is_refused(project, tmp_path):
    '''🔴 Whole would send the private file too: refused, naming the key.'''
    (tmp_path / "secret").mkdir()
    project.set_pdk(two_sources(tmp_path, f"file+private://{tmp_path / 'secret'}"))

    with pytest.raises(owners.PrivateBeside, match=r"library,mixed,package,doc,datasheet"):
        uploaded_by_owner(project)

    # The server's half leaves the parameter out rather than refusing.
    assert not [where for where in owners.collection_keys(
        project, lambda one: owners.uploads(project, one.key, one.dataroot, one.resolvers),
        refuse_private=False) if where[0][:2] == ("library", "mixed")]


def test_a_private_parameter_alone_is_left_out_without_a_refusal(project, tmp_path):
    project.set_pdk(private(PDK, "secret", tmp_path / "secret"))

    assert not [where for where in uploaded_by_owner(project)
                if where[0][:2] == ("library", "secret")]


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
    target = collection / collected_path(value)
    target.parent.mkdir(parents=True)
    target.write_text("uploaded\n")

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
    hashed = collected_path(first(project, ("library", "mine", *DATASHEET)))
    archive, digest, size = _upload_without(project, archive, tmp_path, hashed)

    job = stage(server_client, key, token, archive, size)
    response = submit(server_client, key, token, job["id"], digest, size)

    # 🔴 The 202 says `staging`, never `awaiting_input` (surface D151): the
    # ask goes back through the one backwards edge, from `staging`.
    assert response.status_code == 202
    assert response.get_json()["state"] == "staging"

    from test_server_sources_flow import wait_for

    def read():
        return call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert wait_for(lambda: read()["state"] == "awaiting_input")
    assert read()["upload_sources"] == [{"kind": "dataroot", "name": "mine", "dataroot": "mine"}]
    assert not dispatcher.submitted


def test_a_private_pdk_the_server_has_no_copy_of_is_refused(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    from conftest import call, outcome, slug
    from test_server_jobs import stage, submit

    project = _nop_asic(gcd_design, tmp_path, private(PDK, "secret", tmp_path))
    archive, digest, size = job_archive(project)
    job = stage(server_client, key, token, archive, size)
    response = outcome(server_client, key, token,
                       submit(server_client, key, token, job["id"], digest, size))

    assert response.status_code == 422
    assert slug(response) == "resource-unavailable"
    assert (response.get_json()["resource_kind"], response.get_json()["resource"]) == \
        ("pdk", "secret")
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "rejected"


def test_a_private_design_file_is_refused_while_staging_without_a_kind(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''The backstop for a private source the descriptor never listed: the
    manifest's read finds it, and `resource_kind` is given only for a
    resource's kind -- never the design (surface D285).'''
    from conftest import call, outcome, slug
    from test_server_jobs import stage, submit

    project = _nop_asic(gcd_design, tmp_path, resource(PDK, "mine", tmp_path / "pdk"))
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "top.v").write_text("module top; endmodule\n")
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("mine", f"file+private://{tmp_path / 'secret'}")
    with design.active_dataroot("mine"), design.active_fileset("secret"):
        design.add_file("top.v")
    project.add_fileset("secret")
    archive, digest, size = job_archive(project)
    job = stage(server_client, key, token, archive, size)
    response = outcome(server_client, key, token,
                       submit(server_client, key, token, job["id"], digest, size))

    assert slug(response) == "resource-unavailable"
    body = response.get_json()
    assert body["resource"] == "gcd"
    assert "resource_kind" not in body
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
    from conftest import run_manifest

    # What the run executes: the upload, with the server's overrides applied.
    ran = run_manifest(dispatcher.submitted[0][2])
    assert str(root) in ran.get("library", "secret", "dataroot", "secret", "path")
    assert str(tmp_path / "client-copy") not in json.dumps(ran.getdict()["library"])
    assert "sc_collected_files" in ran.get("library", "gcd", "dataroot",
                                           "gcd-pytest-example", "path")


@pytest.mark.parametrize("key", [
    ("library", "default", "fileset", "rtl", "file", "verilog"),
    ("history", "job0", "option", "builddir"),
    ("option", "credentials"),
    ("tool", "openroad", "task", "place", "output", "place", "0"),
    ("library", "gcd", "fileset", "rtl", "file", "verilog"),
    ("tool", "openroad", "task", "place", "script"),
])
def test_what_is_skipped_is_what_collect_leaves_out(key):
    '''🔴 One rule at both ends (CORE-FOLLOWUPS item 6): the client's copy had
    drifted, keeping a template's `default` keypath the collection drops.'''
    from siliconcompiler.utils.curation import filter_collection_keys

    assert owners.skipped(key) == (filter_collection_keys([(key, None, None)]) == [])
