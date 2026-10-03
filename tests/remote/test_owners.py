import json
import os
import shutil
import sys

from pathlib import Path

import pytest

from siliconcompiler import ASIC, PDK, StdCellLibrary
from siliconcompiler.remote import owners


# What goes in a remote run's archive, and the server's accounting for the rest.

DATASHEET = ("package", "doc", "datasheet")
GITHUB = "https://github.com/siliconcompiler/x/archive/"
RTL = ("library", "gcd", "fileset", "rtl", "file", "verilog")


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


def private(cls, name, root):
    obj = cls(name)
    obj.set_dataroot(name, f"file+private://{root}")
    with obj.active_dataroot(name):
        obj.set(*DATASHEET, "datasheet.pdf")
    return obj


@pytest.fixture
def project(gcd_design):
    return ASIC(gcd_design)


def first(project, key, n=0):
    '''The ``n``th value of a parameter, out of the list it may be held in.'''
    value = project.get(*key, field=None).getvalues(return_values=False)[0][0]
    return value.values[n] if hasattr(value, "values") else value


def collected_path(project, key, n=0):
    '''Where `collect` puts the ``n``th value of ``key``, relative to the
    collection: bucketed by a name only its own resolver knows.'''
    path = first(project, key, n).get()
    for one in owners._values(project):
        if one.key == tuple(key) and one.value.get() == path:
            return owners.collected_path(one)
    raise AssertionError(f"{key} has no value {path}")


def decide(project, key, n=0):
    '''What `collect`'s selector is asked about the ``n``th value: its source,
    and whether it goes up.'''
    value = first(project, key, n)
    resolvers = project.get(*key[:-1], field="schema")._find_files_dataroot_resolvers(True)
    dataroot = value.get(field="dataroot")
    return (owners.source(resolvers, dataroot),
            owners.uploads(project, key, dataroot, resolvers))


def test_every_owner_is_told_apart(project, tmp_path):
    '''PDK and StdCellLibrary subclass Design, so they are tested first --
    the other way round every PDK is the user's design and always uploaded.'''
    project.set_pdk(resource(PDK, "mypdk", tmp_path / "pdk"))
    project.set_mainlib(resource(StdCellLibrary, "mylib", tmp_path / "lib"))

    assert owners.owner(project, ("library", "mypdk", *DATASHEET)) == ("pdk", "mypdk")
    assert owners.owner(project, ("library", "mylib", *DATASHEET)) == ("library", "mylib")
    assert owners.owner(project, RTL) == (owners.DESIGN, "gcd")
    assert owners.owner(project, ("tool", "openroad", "task", "x", "script")) == \
        ("tool", "openroad")
    assert owners.owner(project, ("option", "builddir")) == (owners.PROJECT, None)


def test_the_design_always_goes_up_and_the_credentials_file_never(project, tmp_path):
    '''The credentials file is a path parameter, and this machine's key.'''
    (tmp_path / "credentials").write_text("{}")
    project.option.set_credentials(str(tmp_path / "credentials"))

    assert decide(project, RTL)[1]
    assert not decide(project, ("option", "credentials"))[1]


@pytest.mark.parametrize("root,editable,origin,uploads", [
    # The SOURCE decides, never where the file is now: a lambdapdk PDK is
    # fetched into the cache on first use, so every file it names IS on disk.
    ("https://example.test/pdk.tar.gz", False, owners.REMOTE, False),
    ("{tmp}/pdk", False, owners.LOCAL, True),
    # D112, reversing D109: the server never expands a variable, so the
    # client does, with its own environment, and uploads what it finds.
    ("$FOUNDRY_ROOT", False, owners.LOCAL, True),
    ("dataroot://real", False, owners.REMOTE, False),       # judged by the one it names
    ("python://some_pdk_package", False, owners.INSTALLED, False),
    ("python://some_pdk_package", True, owners.EDITABLE, True),
])
def test_a_pdk_goes_up_by_where_its_dataroot_says_it_comes_from(
        project, tmp_path, monkeypatch, root, editable, origin, uploads):
    from siliconcompiler.package import PythonPathResolver

    monkeypatch.setattr(PythonPathResolver, "is_python_module_editable",
                        staticmethod(lambda module: editable))
    (tmp_path / "pdk").mkdir()
    (tmp_path / "pdk" / "datasheet.pdf").write_text("the datasheet\n")
    monkeypatch.setenv("FOUNDRY_ROOT", str(tmp_path / "pdk"))
    pdk = PDK("mypdk")
    pdk.set_dataroot("real", "https://example.test/pdk.tar.gz", tag="v1")
    pdk.set_dataroot("mypdk", root.format(tmp=tmp_path),
                     tag="v1" if root.startswith("https") else None)
    with pdk.active_dataroot("mypdk"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(pdk)

    assert decide(project, ("library", "mypdk", *DATASHEET)) == (origin, uploads)


@pytest.mark.parametrize("scheme", [
    "file+private", "git+private", "git+https+private", "git+ssh+private",
    "ssh+private", "http+private", "https+private"])
def test_every_private_scheme_is_private_before_any_other_rule(project, tmp_path, scheme):
    '''A `+private` suffix on any scheme (D274): never uploaded, even from
    this disk; a remote one sends its cleaned source and ref (D308), a local none.'''
    local = scheme == "file+private"
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "datasheet.pdf").write_text("x")
    source = f"{scheme}://{tmp_path / 'secret'}" if local else \
        f"{scheme}://alice:ghp_TOKEN@host/secret.git?k=v"
    pdk = PDK("secret")
    pdk.set_dataroot("secret", source, tag=None if local else "v1")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(pdk)

    assert decide(project, ("library", "secret", *DATASHEET)) == (owners.PRIVATE, False)
    entry, = [item for item in owners.sources(project)
              if item["keypath"] == ["library", "secret", "dataroot", "secret"]]
    assert entry["private"] is True
    if local:
        assert "source" not in entry and "ref" not in entry
        assert str(tmp_path) not in json.dumps(entry)
    else:
        assert entry["source"].endswith("://host/secret.git?k=***") and entry["ref"] == "v1"
        assert "ghp_TOKEN" not in entry["source"] and "alice" not in entry["source"]


def test_the_marker_is_tested_in_one_place():
    '''A `+private` scheme, on a local path or a fetched source alike.'''
    from siliconcompiler.package import FileResolver
    from siliconcompiler.package.git import GitResolver

    assert owners.is_private(FileResolver("x", None, "file+private:///a"))
    assert owners.is_private(GitResolver("x", None, "git+ssh+private://host/a.git", "v1"))
    assert not owners.is_private(FileResolver("x", None, "/a"))
    assert not owners.is_private(GitResolver("x", None, "git+ssh://host/a.git", "v1"))


def test_sources_name_what_is_not_uploaded_as_both_ends_read_it_without_a_credential(
        project, tmp_path):
    '''`safe_source` (#5454): no userinfo, every query value masked -- one
    string in the client's `sources` and the server's `value_records`.'''
    project.set_pdk(resource(
        PDK, "lambda", "https://user:ghp_x@github.com/siliconcompiler/x/archive/v1.tar.gz"
        "?access_token=SECRET&lfs=true", create=False))
    project.add_asiclib(private(StdCellLibrary, "secretlib", tmp_path))

    listed = {tuple(item["keypath"]): item for item in owners.sources(project)}
    record, = [one for one in owners.value_records(owners.without_credentials(project), "none")
               if one["key"][:2] == ["library", "lambda"]]

    assert not any("kind" in item for item in listed.values())       # by keypath (D298)
    assert not any(keypath[1] == "gcd" for keypath in listed)
    sent = listed[("library", "lambda", "dataroot", "lambda")]
    assert sent["source"] == ("https://github.com/siliconcompiler/x/archive/v1.tar.gz"
                              "?access_token=***&lfs=***")
    assert (sent["ref"], sent["private"]) == ("v1", False)
    assert record["source"] == sent["source"]
    assert owners.is_masked(sent["source"]) and not owners.is_masked(GITHUB)
    hidden = listed[("library", "secretlib", "dataroot", "secretlib")]
    assert hidden["private"] is True and "source" not in hidden


def test_every_dataroot_path_leaves_without_its_credential(gcd_nop_project):
    '''D302: the design's, a private one, a task's query, and the same in the
    history -- on a copy, so the user's project keeps what they registered.'''
    assert owners.without_credentials(gcd_nop_project) is gcd_nop_project   # none: no copy
    project = gcd_nop_project
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("ip", "git+https://alice:TOKEN@example.com/ip.git", "v1")
    design.set_dataroot("secret", "git+https+private://alice:TOKEN@example.com/secret.git",
                        "v1")
    project.set("tool", "builtin", "task", "nop", "dataroot", "scripts", "path",
                "https://example.com/scripts.tar.gz?token=TOKEN")
    project._record_history()

    paths = dict(owners.dataroot_paths(owners.without_credentials(project)))

    assert paths[("library", "gcd", "dataroot", "ip")] == "git+https://example.com/ip.git"
    assert paths[("library", "gcd", "dataroot", "secret")] == \
        "git+https+private://example.com/secret.git"
    assert paths[("tool", "builtin", "task", "nop", "dataroot", "scripts")] == \
        "https://example.com/scripts.tar.gz?token=***"
    assert paths[("history", "job0", "library", "gcd", "dataroot", "ip")] == \
        "git+https://example.com/ip.git"
    assert not any("TOKEN" in path or owners.has_userinfo(path) for path in paths.values())
    assert project.get("library", "gcd", "dataroot", "ip", "path") == \
        "git+https://alice:TOKEN@example.com/ip.git"


def test_userinfo_is_read_as_the_mask_reads_it():
    '''What the client strips and the server refuses: anything ahead of the
    host, `git@` included, and nothing in the path.'''
    for url in ("git+https://alice:TOKEN@example.com/ip.git",
                "git+ssh://git@github.com/acme/ip.git", "https://TOKEN@example.com/x"):
        assert owners.has_userinfo(url)
        assert not owners.has_userinfo(owners.masked(url))
    for url in ("git+https://example.com/ip.git@v1", "/home/me@corp/ip", "", None):
        assert not owners.has_userinfo(url)


def test_a_masked_source_is_never_fetched(project, tmp_path):
    '''With the server's own supply and everything allowlisted: a public
    masked source is asked for; a private one only supplied by a copy.'''
    from siliconcompiler.remote.server.jobs.common import _Supply

    def supply(private=None, held=None):
        return _Supply({"private_dataroots": private or {}, "fetch_fails": False},
                       Supply(held=held, allowed=[""]))

    project.set_pdk(resource(PDK, "lambda", f"{GITHUB}?token=SECRET", create=False))
    assert status(owners.without_credentials(project), "lambda", supply()).status == \
        owners.ASK

    secret = PDK("secret")
    secret.set_dataroot("secret", "https+private://github.com/siliconcompiler/s/?token=SECRET",
                        tag="v1")
    with secret.active_dataroot("secret"):
        secret.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(secret)
    sent = owners.without_credentials(project)
    masked = "https://github.com/siliconcompiler/s/?token=***"
    (tmp_path / "datasheet.pdf").write_text("x")
    assert status(sent, "secret", supply()).status == owners.UNAVAILABLE
    assert status(sent, "secret", supply(held={(masked, "v1"): str(tmp_path)})).status == \
        owners.SUPPLIED
    library = {"library": {"secret": {"secret": str(tmp_path)}}}
    assert status(sent, "secret", supply(private=library)).status == owners.SUPPLIED


def uploaded_by_owner(project):
    '''What a remote run hands `collect`, by the owner rule alone.'''
    return owners.collection(project, lambda one: owners.uploads(
        project, one.key, one.dataroot, one.resolvers))


def collect_by_owner(project):
    from siliconcompiler.utils.curation import collect

    chosen = uploaded_by_owner(project)
    collect(project, keys=chosen.keys, select=chosen.select, verbose=False)


def collected_names(project):
    from siliconcompiler.utils.paths import collectiondir

    return [name for _, _, names in os.walk(collectiondir(project)) for name in names]


def test_collect_takes_what_the_owner_rule_selects_and_no_flag_is_touched(
        project, tmp_path):
    project.option.set_builddir(str(tmp_path / "build"))
    project.set_pdk(resource(PDK, "local", tmp_path / "pdk"))
    project.add_asiclib(resource(StdCellLibrary, "remote",
                                 "https://example.test/lib.tar.gz", create=False))
    project.add_asiclib(private(StdCellLibrary, "secret", tmp_path / "secret"))
    # A private parameter alone is left out, and nothing refused.
    assert not [where for where in uploaded_by_owner(project).keys
                if where[0][:2] == ("library", "secret")]

    collect_by_owner(project)

    taken = collected_names(project)
    assert "gcd.v" in taken
    assert taken.count("datasheet.pdf") == 1        # the local one: none fetched
    # The caller's project is not rewritten to get there.
    assert not project.get("library", "local", *DATASHEET, field="copy")


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Making a symbolic link needs a privilege on Windows")
def test_a_file_with_many_names_is_reported_once_and_accounted_under_each():
    '''Stored once, every other name a link carrying no bytes: the report says
    what the archive holds, and each value is found once the sources are gone.'''
    from siliconcompiler import Design, Lint
    from siliconcompiler.utils.paths import collectiondir

    os.makedirs("proj/rtl")
    with open("proj/rtl/a.v", "w") as f:
        f.write("module a; endmodule\n")
    with open("proj/rtl/defs.vh", "w") as f:
        f.write("`define WIDTH 8\n")
    os.symlink("defs.vh", "proj/rtl/alias.vh")
    # `a.v` twice: in `top`'s `rtl` directory, and as a file under `rtl`.
    design = Design("top")
    design.set_dataroot("top", os.path.abspath("proj"))
    design.set_dataroot("rtl", os.path.abspath("proj/rtl"))
    design.set_topmodule("a", fileset="rtl")
    design.add_idir("rtl", dataroot="top", fileset="rtl")
    design.add_file("a.v", dataroot="rtl", fileset="rtl")
    project = Lint(design)
    project.add_fileset("rtl")

    collect_by_owner(project)

    collection = collectiondir(project)
    report = owners.upload_report(project, collection)
    assert sum(row[3] for row in report) == \
        os.path.getsize("proj/rtl/a.v") + os.path.getsize("proj/rtl/defs.vh")
    assert sum(row[4] for row in report) == 2
    shutil.move("proj", "moved")
    assert {(entry.dataroot, entry.status) for entry in
            account(project, collection, Supply())} == \
        {("top", owners.UPLOADED), ("rtl", owners.UPLOADED)}


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


@pytest.mark.parametrize("second,origin", [
    ("https://example.test/pdk.tar.gz", owners.REMOTE),     # never resolved, never fetched
    # It must not leave this machine, and nothing is refused for it.
    ("file+private://{tmp}/secret", owners.PRIVATE),
])
def test_a_value_goes_up_on_its_own(project, tmp_path, second, origin):
    '''Surface *A parameter may go up in part*: the local value goes up, the
    one beside it in the same parameter stays behind.'''
    project.option.set_builddir(str(tmp_path / "build"))
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "other.pdf").write_text("private\n")
    project.set_pdk(two_sources(tmp_path, second.format(tmp=tmp_path)))
    key = ("library", "mixed", *DATASHEET)
    assert [decide(project, key, n)[0] for n in (0, 1)] == [owners.LOCAL, origin]

    collect_by_owner(project)

    taken = collected_names(project)
    assert "datasheet.pdf" in taken and "other.pdf" not in taken


class Supply:
    '''A server, as `account_records` asks it.'''

    def __init__(self, packages=(), private=None, held=None, allowed=()):
        self.packages, self.private = set(packages), private or {}
        self.held_roots, self.allowed = held or {}, list(allowed)

    def package(self, module):
        return module in self.packages

    def private_root(self, keypath):
        return self.private.get(tuple(keypath))

    def held(self, source, ref):
        return self.held_roots.get((source, ref))

    def allowlisted(self, source, ref):
        return any(str(source).startswith(prefix) for prefix in self.allowed)


def account(project, collection_dir, supply, required=None):
    '''How a server accounts for ``project``: its `value_records`, read where
    the manifest is, then `account_records`.'''
    return owners.account_records(owners.value_records(project, collection_dir, required),
                                  collection_dir, supply, required)


def status(project, name, supply, collection="none"):
    for entry in account(project, collection, supply):
        if entry.name == name:
            return entry
    raise AssertionError(f"{name} not accounted for")


@pytest.mark.parametrize("root,supply,expected", [
    # The live hole (D112): rooted at `/etc`, left out of the archive, and
    # the file IS on this machine -- asked of the client, never looked for.
    ("/etc", {}, owners.ASK),
    (GITHUB, {"allowed": ["https://github.com/siliconcompiler/"]}, owners.FETCH),
    (GITHUB, {}, owners.ASK),           # off the allowlist: asked of the client, not refused
    (GITHUB, {"held": True}, owners.SUPPLIED),                    # from the server's copy
    ("python://some_pdk_package", {"packages": ["some_pdk_package"]}, owners.SUPPLIED),
    ("python://some_pdk_package", {}, owners.ASK),
])
def test_a_file_not_uploaded_is_supplied_fetched_or_asked_for(
        project, tmp_path, root, supply, expected):
    project.set_pdk(resource(PDK, "pdk", root, create=False,
                             file="passwd" if root == "/etc" else "datasheet.pdf"))
    held = {(GITHUB, "v1"): str(tmp_path)} if supply.get("held") else None

    entry = status(project, "pdk", Supply(**dict(supply, held=held)))

    assert entry.status == expected
    if expected == owners.FETCH:
        assert (entry.source, entry.ref) == (GITHUB, "v1")
    if held:
        assert entry.root == str(tmp_path)


def test_an_uploaded_file_is_accounted_as_uploaded(project, tmp_path):
    project.set_pdk(resource(PDK, "mine", tmp_path / "pdk"))
    collection = tmp_path / "sc_collected_files"
    target = collection / collected_path(project, ("library", "mine", *DATASHEET))
    target.parent.mkdir(parents=True)
    target.write_text("uploaded\n")

    assert status(project, "mine", Supply(), collection).status == owners.UPLOADED


def test_a_private_design_is_supplied_like_any_other(project, tmp_path):
    '''D299: *designs can have private data for the same reason* -- supplied
    from the operator's copy, refused in the same words where there is none.'''
    (tmp_path / "top.v").write_text("module top; endmodule\n")
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("mine", f"file+private://{tmp_path}")
    with design.active_dataroot("mine"), design.active_fileset("rtl"):
        design.add_file("top.v")
    mine = ("library", "gcd", "dataroot", "mine")

    def entry(supply):
        found, = [one for one in account(project, "none", supply) if one.dataroot == "mine"]
        return found

    supplied = entry(Supply(private={mine: str(tmp_path)}))
    assert (supplied.status, supplied.root) == (owners.SUPPLIED, str(tmp_path))
    missing = entry(Supply())
    assert missing.status == owners.UNAVAILABLE
    assert missing.why.startswith("a private dataroot this server has no copy of, and "
                                  "cannot fetch either")
    assert decide(project, RTL) != (owners.PRIVATE, True)


def test_a_path_escaping_a_supplied_root_is_refused_links_and_all(project, tmp_path):
    root = tmp_path / "root"
    (root / "inside").mkdir(parents=True)
    (root / "inside" / "ok.lef").write_text("x")
    (root / "escape").symlink_to("/etc")
    assert owners.confined(root, "inside/ok.lef") == \
        str((root / "inside" / "ok.lef").resolve())
    for way_out in ("escape/passwd", "../outside", "/etc/passwd"):
        assert owners.confined(root, way_out) is None

    pdk = private(PDK, "secret", "/anywhere")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "../../etc/passwd")
    project.set_pdk(pdk)
    secret = ("library", "secret", "dataroot", "secret")
    assert status(project, "secret", Supply(private={secret: str(root)})).status == \
        owners.UNAVAILABLE


def test_a_private_dataroot_is_supplied_by_the_first_of_three_and_never_asked_for(
        project, tmp_path):
    '''D299: the operator's copy, a held copy of its source, a fetch from the
    allowlist -- and UNAVAILABLE where none answers, never ASK.'''
    pdk = PDK("secret")
    pdk.set_dataroot("secret", GITHUB.replace("https", "https+private", 1), tag="v1")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(pdk)
    keypath = ("library", "secret", "dataroot", "secret")
    (tmp_path / "datasheet.pdf").write_text("x")
    record, = [one for one in owners.value_records(project, "none")
               if one["key"][:2] == ["library", "secret"]]

    # The manifest's own source, masked as any source is, and never uploaded.
    assert (record["origin"], record["source"], record["ref"]) == \
        (owners.PRIVATE, GITHUB, "v1")
    assert decide(project, ("library", "secret", *DATASHEET)) == (owners.PRIVATE, False)

    def entry(supply):
        found, = [one for one in account(project, "none", supply) if one.keypath == keypath]
        return found

    mapped = entry(Supply(private={keypath: str(tmp_path)}, allowed=[GITHUB]))
    assert (mapped.status, mapped.root) == (owners.SUPPLIED, str(tmp_path))
    assert entry(Supply(held={(GITHUB, "v1"): str(tmp_path)})).status == owners.SUPPLIED
    assert entry(Supply(allowed=[GITHUB])).status == owners.FETCH
    assert entry(Supply()).status == owners.UNAVAILABLE


@pytest.fixture
def dispatcher(server):
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


def submit_project(server_client, key, token, job_archive, project, left_out=None):
    '''``project``'s archive, without ``left_out``, staged and submitted: the
    job, and what the submit came to (`conftest.outcome`).'''
    from conftest import outcome
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive(project)
    if left_out:
        archive, digest, size = _upload_without(project, archive, Path.cwd(), left_out)
    job = stage(server_client, key, token, archive, size)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


def test_a_local_pdk_left_out_is_asked_for_not_supplied_from_the_host(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path):
    '''The file is on this machine, and the job is asked for it.'''
    from test_server_sources_flow import read, wait_for

    project = _nop_asic(gcd_design, tmp_path, resource(PDK, "mine", tmp_path / "pdk"))
    job, response = submit_project(
        server_client, key, token, job_archive, project,
        left_out=collected_path(project, ("library", "mine", *DATASHEET)))

    # The 202 says `staging`, never `awaiting_input` (D151): the ask goes
    # back through the one backwards edge, from `staging`.
    assert (response.status_code, response.get_json()["state"]) == (202, "staging")
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")
    assert read(server_client, key, token, job["id"])["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "mine", "dataroot", "mine"]}]
    assert not dispatcher.submitted


@pytest.mark.parametrize("design", [False, True], ids=["pdk", "design"])
def test_a_private_source_the_server_has_no_copy_of_is_refused(
        server_client, key, token, job_archive, dispatcher, gcd_design, tmp_path, design):
    '''A PDK names its `resource_kind`; a design file -- found by the manifest's
    read, the backstop for a source the descriptor never listed -- none (D285).'''
    from conftest import slug
    from test_server_sources_flow import read

    if design:
        project = _nop_asic(gcd_design, tmp_path, resource(PDK, "mine", tmp_path / "pdk"))
        (tmp_path / "secret").mkdir()
        (tmp_path / "secret" / "top.v").write_text("module top; endmodule\n")
        schema = project.get("library", "gcd", field="schema")
        schema.set_dataroot("mine", f"file+private://{tmp_path / 'secret'}")
        with schema.active_dataroot("mine"), schema.active_fileset("secret"):
            schema.add_file("top.v")
        project.add_fileset("secret")
    else:
        project = _nop_asic(gcd_design, tmp_path, private(PDK, "secret", tmp_path))

    job, response = submit_project(server_client, key, token, job_archive, project)

    assert (response.status_code, slug(response)) == (422, "resource-unavailable")
    assert (response.get_json()["resource"], response.get_json().get("resource_kind")) == \
        (("gcd", None) if design else ("secret", "pdk"))
    assert read(server_client, key, token, job["id"])["state"] == "rejected"


def test_a_mapped_private_pdk_runs_and_the_manifest_says_whose_copy(
        server, server_client, key, token, job_archive, dispatcher, gcd_design,
        tmp_path):
    '''The operator's copy, confined -- and the manifest the run loads points
    each dataroot at the copy it resolves to (D111).'''
    from conftest import run_manifest
    from siliconcompiler.remote.server.running import runspec

    root = tmp_path / "operator-copy"
    root.mkdir()
    (root / "datasheet.pdf").write_text("x")
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"secret": {"secret": str(root)}}}
    (tmp_path / "client-copy").mkdir()
    (tmp_path / "client-copy" / "datasheet.pdf").write_text("x")
    project = _nop_asic(gcd_design, tmp_path,
                        private(PDK, "secret", tmp_path / "client-copy"))

    _, response = submit_project(server_client, key, token, job_archive, project)

    assert response.status_code == 202, response.get_json()
    ran = run_manifest(dispatcher.submitted[0][2])     # with the server's overrides applied
    assert str(root) in ran.get("library", "secret", "dataroot", "secret", "path")
    assert str(tmp_path / "client-copy") not in json.dumps(ran.getdict()["library"])
    # The design's dataroot rebuilt under the job, where the run finds its files.
    uploaded = ran.get("library", "gcd", "dataroot", "gcd-pytest-example", "path")
    assert f"/{runspec.UPLOADS_DIRNAME}/" in uploaded
    assert ran.find_files(*RTL)[0].startswith(uploaded)


@pytest.mark.parametrize("key", [
    ("library", "default", "fileset", "rtl", "file", "verilog"),
    ("history", "job0", "option", "builddir"),
    ("option", "credentials"),
    ("tool", "openroad", "task", "place", "output", "place", "0"),
    RTL,
    ("tool", "openroad", "task", "place", "script"),
])
def test_what_is_skipped_is_what_collect_leaves_out(key):
    '''One rule at both ends: the client's copy had drifted, keeping a
    template's `default` keypath the collection drops.'''
    from siliconcompiler.utils.curation import filter_collection_keys

    assert owners.skipped(key) == (filter_collection_keys([(key, None, None)]) == [])


RUN = ("tool", "acme_sim", "task", "run", "dataroot", "scripts")
CHECK = ("tool", "acme_sim", "task", "check", "dataroot", "scripts")


def acme_project(gcd_design):
    '''Two tasks of one tool, each with a `scripts` dataroot of its own.'''
    from siliconcompiler import Flowgraph
    from pytasks import AcmeCheck, AcmeRun

    project = ASIC(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("acmeflow")
    flow.node("run", AcmeRun())
    flow.node("check", AcmeCheck())
    flow.edge("run", "check")
    project.set_flow(flow)
    return project


@pytest.mark.parametrize("keypath,shaped", [
    (["library", "gcd", "dataroot", "root"], True),
    (["tool", "acme_sim", "task", "run", "dataroot", "scripts"], True),
    (["tool", "acme_sim", "dataroot", "scripts"], False),     # a tool's, with no task
    (["library", "gcd"], False),
    (["option", "x", "dataroot", "y"], False),
    (["library", "gcd", "dataroot", ""], False),
    ("library,gcd,dataroot,root", False),
    (["library", "gcd", "dataroot", 1], False),
])
def test_a_keypath_is_a_librarys_or_a_tasks_and_nothing_else(keypath, shaped):
    assert owners.is_dataroot_keypath(keypath) is shaped


def test_the_keypath_is_where_the_dataroot_is_defined(gcd_design):
    '''Never a slice of the parameter's key: a design's fileset value is its
    library's, however deep the fileset, and a task's `refdir` its task's.'''
    project = acme_project(gcd_design)
    dataroot = first(project, RTL).get(field="dataroot")

    assert owners.dataroot_keypath(project, RTL, dataroot) == \
        ("library", "gcd", "dataroot", dataroot)
    assert owners.dataroot_keypath(project, ("tool", "acme_sim", "task", "run", "refdir"),
                                   "scripts") == RUN
    # No dataroot, or one its owner does not define: local, and uploaded.
    assert owners.dataroot_keypath(project, RTL, None) is None
    assert owners.dataroot_keypath(project, RTL, "nowhere") is None
    assert {one.keypath for one in owners._values(project) if one.key == RTL} == \
        {("library", "gcd", "dataroot", dataroot)}


def test_two_tasks_of_one_tool_and_a_library_of_its_name_are_three_dataroots(
        gcd_design, tmp_path):
    '''A task's dataroot was once named by its tool, so two tasks' `scripts`
    were one entry: each is listed, accounted, collected and pointed apart.'''
    from pytasks import AcmeCheck, AcmeRun
    from siliconcompiler.remote.server.running import runspec

    project = acme_project(gcd_design)
    acme = "https://github.com/siliconcompiler/acme/"
    project.set_pdk(resource(PDK, "acme_sim", acme, create=False))
    library = ("library", "acme_sim", "dataroot", "acme_sim")

    listed = {tuple(item["keypath"]): item["source"] for item in owners.sources(project)}
    assert listed == {library: acme, RUN: AcmeRun.SOURCE, CHECK: AcmeCheck.SOURCE}
    asked = [entry.wire for entry in account(project, "none", Supply())
             if entry.origin == owners.REMOTE]
    assert sorted(tuple(item["keypath"]) for item in asked) == sorted([library, RUN, CHECK])
    picked = owners.collection(project, lambda one: one.keypath == RUN)
    assert [key for key, _, _ in picked.keys] == [("tool", "acme_sim", "task", "run", "refdir")]

    # `runspec.point_dataroots`: never both at whichever copy came first.
    targets = runspec.dataroot_targets([
        owners.Entry("tool", "acme_sim", "scripts", owners.SUPPLIED,
                     root=str(tmp_path / "run"), keypath=RUN),
        owners.Entry("tool", "acme_sim", "scripts", owners.SUPPLIED,
                     root=str(tmp_path / "check"), keypath=CHECK),
        owners.Entry("design", "gcd", None, owners.UPLOADED)], tmp_path / "collection")
    assert runspec.point_dataroots(project, targets) == 2
    assert project.get(*RUN, "path") == str(tmp_path / "run")
    assert project.get(*CHECK, "path") == str(tmp_path / "check")


def test_a_dataroot_no_keypath_names_stops_the_client_before_create(
        project, monkeypatch, logged_in):
    '''The server refuses a keypath of any other shape, so the client says so
    first, naming the parameter.'''
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun

    project.set_pdk(resource(PDK, "lambda", "https://github.com/siliconcompiler/x/",
                             create=False))
    monkeypatch.setattr(owners, "dataroot_keypath",
                        lambda project, key, dataroot: ("elsewhere", "dataroot", dataroot))

    with pytest.raises(owners.Unnamed, match=r"\[library,lambda,package,doc,datasheet\]"):
        owners.sources(project)
    with pytest.raises(RemoteError, match="neither a library's nor a task's"):
        RemoteRun(project, logged_in)._check_dataroots()


@pytest.mark.parametrize("masked,collects", [(False, False), (False, True), (True, False)],
                         ids=["as-run", "collected-again", "masked-query"])
def test_an_uploaded_file_is_found_by_the_run_once_its_dataroot_is_pointed(
        tmp_path, monkeypatch, masked, collects):
    '''Collected, sent masked, pointed and found at the rebuilt dataroot --
    even collected again, as a Slurm run is -- never fetched (#5471).'''
    from siliconcompiler import Design, Lint
    from siliconcompiler.package.https import HTTPResolver
    from siliconcompiler.remote.server.running import runspec
    from siliconcompiler.schema import BaseSchema
    from siliconcompiler.utils.curation import collect

    copy = tmp_path / "submitter" / "top"
    (copy / "rtl").mkdir(parents=True)
    (copy / "rtl" / "top.v").write_text("module top; endmodule\n")
    design = Design("top")
    if masked:
        # The download, on the client: no network here.
        monkeypatch.setattr(HTTPResolver, "resolve", lambda self: str(copy))
        design.set_dataroot("top", "https://example.com/ip/archive/?token=SECRET", tag="v1")
    else:
        design.set_dataroot("top", str(copy))
    design.set_topmodule("top", fileset="rtl")
    design.add_file("rtl/top.v", dataroot="top", fileset="rtl")
    project = Lint(design)
    project.add_fileset("rtl")

    tree = tmp_path / "job" / "top" / "job0"
    collection = tree / "sc_collected_files"
    chosen = uploaded_by_owner(project)
    collect(project, keys=chosen.keys, directory=str(collection), verbose=False,
            select=chosen.select)
    owners.without_credentials(project).write_manifest(str(tree / "top.pkg.json"))
    assert "SECRET" not in (tree / "top.pkg.json").read_text()
    shutil.rmtree(tmp_path / "submitter")
    monkeypatch.setattr(HTTPResolver, "resolve",
                        lambda self: pytest.fail("the server fetched a masked source"))

    run = Lint.from_manifest(filepath=str(tree / "top.pkg.json"))
    keypath = ("library", "top", "dataroot", "top")
    record, = [one for one in owners.value_records(run, str(collection))
               if one["key"][:2] == ["library", "top"]]
    assert record["collected"], "the upload is not where the manifest looks"
    targets = runspec.dataroot_targets(
        [owners.Entry("design", "top", "top", owners.UPLOADED, keypath=keypath)], collection)
    assert runspec.point_dataroots(run, targets) == 1
    assert run.get(*keypath, "path").startswith(str(tmp_path / "job" / "sc-server-uploads"))
    if collects:
        collect(run, keys=[(("library", "top", "fileset", "rtl", "file", "verilog"),
                            None, None)], verbose=False)

    found, = BaseSchema._find_files(run, "library", "top", "fileset", "rtl", "file", "verilog",
                                    collection_dir=str(collection))
    assert found.startswith(str(tmp_path / "job"))
    with open(found) as f:
        assert f.read() == "module top; endmodule\n"
