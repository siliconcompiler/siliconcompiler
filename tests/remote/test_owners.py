import json
import os
import shutil
import sys

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


def collected_path(project, key, n=0):
    '''Where `collect` puts the ``n``th value of ``key``, under the collection
    directory: bucketed by its dataroot's collected name, which only the
    value's own resolver knows (`owners.collected_path`).'''
    path = first(project, key, n).get()
    for one in owners._values(project):
        if one.key == tuple(key) and one.value.get() == path:
            return owners.collected_path(one)
    raise AssertionError(f"{key} has no value {path}")


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
    uploaded. A remote one carries its cleaned source and ref (surface D308),
    and a local one neither -- its path is never sent.'''
    local = scheme == "file+private"
    source = f"{scheme}://{tmp_path / 'secret'}" if local else f"{scheme}://host/secret.git"
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
        assert entry["source"].endswith("://host/secret.git") and entry["ref"] == "v1"


def test_a_private_remote_source_is_sent_without_its_credentials(project):
    '''As every other source is: no userinfo, and every query value masked.'''
    pdk = PDK("secret")
    pdk.set_dataroot("secret", "git+https+private://alice:ghp_TOKEN@host/secret.git?k=v",
                     tag="v1")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(pdk)

    entry, = [item for item in owners.sources(project)
              if item["keypath"] == ["library", "secret", "dataroot", "secret"]]
    assert "ghp_TOKEN" not in entry["source"] and "alice" not in entry["source"]
    assert entry["source"].endswith("host/secret.git?k=***")


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

    listed = {tuple(item["keypath"]): item for item in owners.sources(project)}
    # By keypath, and no kind (surface D298).
    assert not any("kind" in item for item in listed.values())

    remote = listed[("library", "lambda", "dataroot", "lambda")]
    assert remote["source"] == "https://github.com/siliconcompiler/x/archive/"
    assert remote["ref"] == "v1" and remote["private"] is False

    hidden = listed[("library", "secretlib", "dataroot", "secretlib")]
    # 🔴 A private dataroot's path is never sent.
    assert hidden["private"] is True and "source" not in hidden
    assert not any(keypath[1] == "gcd" for keypath in listed)


def test_a_token_in_a_query_never_leaves_this_machine(project):
    '''🔴 What is sent is SiliconCompiler's own `safe_source`: no userinfo,
    and every query value masked, its name kept so the source still says what
    it is (#5454).'''
    project.set_pdk(resource(
        PDK, "lambda",
        "https://user:ghp_x@github.com/siliconcompiler/x/archive/v1.tar.gz"
        "?access_token=SECRET&lfs=true", create=False))

    sent, = [item for item in owners.sources(project) if item["keypath"][1] == "lambda"]

    assert sent["source"] == ("https://github.com/siliconcompiler/x/archive/v1.tar.gz"
                              "?access_token=***&lfs=***")
    assert owners.is_masked(sent["source"])
    assert not owners.is_masked("https://github.com/siliconcompiler/x/archive/")


###########################
# No credential in the manifest (surface D302)
###########################

def with_credentials(project):
    '''Dataroots registered with a credential -- the design's, a private one,
    and a task's with a token in its query -- and the same again in the history
    an earlier run left, which the manifest carries too.'''
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("ip", "git+https://alice:TOKEN@example.com/ip.git", "v1")
    design.set_dataroot("secret", "git+https+private://alice:TOKEN@example.com/secret.git",
                        "v1")
    project.set("tool", "builtin", "task", "nop", "dataroot", "scripts", "path",
                "https://example.com/scripts.tar.gz?token=TOKEN")
    project._record_history()
    return project


def test_every_dataroot_path_leaves_without_its_credential(gcd_nop_project):
    project = with_credentials(gcd_nop_project)

    paths = dict(owners.dataroot_paths(owners.without_credentials(project)))

    assert paths[("library", "gcd", "dataroot", "ip")] == "git+https://example.com/ip.git"
    assert paths[("library", "gcd", "dataroot", "secret")] == \
        "git+https+private://example.com/secret.git"
    assert paths[("tool", "builtin", "task", "nop", "dataroot", "scripts")] == \
        "https://example.com/scripts.tar.gz?token=***"
    assert paths[("history", "job0", "library", "gcd", "dataroot", "ip")] == \
        "git+https://example.com/ip.git"
    assert not any("TOKEN" in path or owners.has_userinfo(path) for path in paths.values())


def test_the_users_own_project_keeps_what_they_registered(gcd_nop_project):
    project = with_credentials(gcd_nop_project)

    owners.without_credentials(project)

    assert project.get("library", "gcd", "dataroot", "ip", "path") == \
        "git+https://alice:TOKEN@example.com/ip.git"


def test_a_project_with_no_credential_is_not_copied(gcd_nop_project):
    assert owners.without_credentials(gcd_nop_project) is gcd_nop_project


def test_userinfo_is_read_as_the_mask_reads_it():
    '''What the client strips and what the server refuses are one thing:
    anything ahead of the host, `git@` included, and nothing in the path.'''
    for url in ("git+https://alice:TOKEN@example.com/ip.git",
                "git+ssh://git@github.com/acme/ip.git", "https://TOKEN@example.com/x"):
        assert owners.has_userinfo(url)
        assert not owners.has_userinfo(owners.masked(url))
    for url in ("git+https://example.com/ip.git@v1", "/home/me@corp/ip", "", None):
        assert not owners.has_userinfo(url)


def test_both_ends_read_one_masked_source(project):
    '''What the descriptor says -- the client's `sources`, from the user's own
    project -- and what the server accounts by -- `value_records` of the
    manifest the client sent -- are one string, so a held copy stored under
    one is found under the other.'''
    project.set_pdk(resource(
        PDK, "lambda",
        "https://user:ghp_x@github.com/siliconcompiler/x/archive/v1.tar.gz"
        "?access_token=SECRET&lfs=true", create=False))

    sent, = [item for item in owners.sources(project) if item["keypath"][1] == "lambda"]
    record, = [one for one in owners.value_records(owners.without_credentials(project), "none")
               if one["key"][:2] == ["library", "lambda"]]

    assert record["source"] == sent["source"]
    assert "SECRET" not in record["source"] and "ghp_x" not in record["source"]


def test_a_masked_source_is_never_fetched(project, tmp_path):
    '''🔴 With the server's own supply, and a source on its allowlist: a
    public one whose query was masked is asked for, and a private one is
    supplied only from the operator's copy or a held copy.'''
    from siliconcompiler.remote.server.jobs.common import _Supply

    class Sources:
        def __init__(self, held=None):
            self._held = held or {}

        def held(self, source, ref):
            return self._held.get((source, ref))

        def allowlisted(self, source, ref):
            return True

    def supply(private=None, held=None):
        return _Supply({"private_dataroots": private or {}, "fetch_fails": False},
                       Sources(held))

    public = "https://github.com/siliconcompiler/x/archive/?token=SECRET"
    project.set_pdk(resource(PDK, "lambda", public, create=False))
    sent = owners.without_credentials(project)
    assert status(sent, "lambda", supply()).status == owners.ASK

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


###########################
# collect(), told what to take: a value at a time
###########################

def uploaded_by_owner(project):
    '''What a remote run hands `collect`, by the owner rule alone.'''
    return owners.collection(project, lambda one: owners.uploads(
        project, one.key, one.dataroot, one.resolvers, one.value.get()))


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

    collect_by_owner(project)

    taken = collected_names(project)
    assert "gcd.v" in taken
    # Remote: not fetched, not collected.
    assert taken.count("datasheet.pdf") == 1

    # 🔴 The caller's project is not rewritten to get there.
    assert not project.get("library", "local", *DATASHEET, field="copy")


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Making a symbolic link needs a privilege on Windows")
def test_a_file_with_many_names_is_reported_once_and_accounted_under_each():
    '''`collect` stores a file once, and every other name for it -- a second
    value, a link in a collected directory -- is a link to that copy, which
    carries no bytes. The report says what the archive holds, and the server
    finds each value at its own collected path once the sources are gone.'''
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
            owners.account(project, collection, Supply())} == \
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


def test_a_value_goes_up_on_its_own(project, tmp_path):
    '''Surface *A parameter may go up in part*: the local value goes up, and
    the remote one beside it in the same parameter stays behind -- never
    resolved, so its source is never fetched here.'''
    project.option.set_builddir(str(tmp_path / "build"))
    project.set_pdk(two_sources(tmp_path, "https://example.test/pdk.tar.gz"))
    key = ("library", "mixed", *DATASHEET)
    assert [decide_value(project, key, n)[0] for n in (0, 1)] == [owners.LOCAL, owners.REMOTE]

    collect_by_owner(project)

    taken = collected_names(project)
    assert "datasheet.pdf" in taken and "other.pdf" not in taken


def test_a_private_value_beside_an_uploaded_one_stays_behind(project, tmp_path):
    '''🔴 It must not leave this machine, and nothing is refused: the rest of
    its parameter goes up without it.'''
    project.option.set_builddir(str(tmp_path / "build"))
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "other.pdf").write_text("private\n")
    project.set_pdk(two_sources(tmp_path, f"file+private://{tmp_path / 'secret'}"))

    collect_by_owner(project)

    taken = collected_names(project)
    assert "datasheet.pdf" in taken and "other.pdf" not in taken


def test_a_private_parameter_alone_is_left_out_without_a_refusal(project, tmp_path):
    project.set_pdk(private(PDK, "secret", tmp_path / "secret"))

    assert not [where for where in uploaded_by_owner(project).keys
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

    def private_root(self, keypath):
        return self.private.get(tuple(keypath))

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
    target = collection / collected_path(project, ("library", "mine", *DATASHEET))
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

    secret = ("library", "secret", "dataroot", "secret")
    mapped = status(project, "secret", Supply(private={secret: str(root)}))
    assert (mapped.status, mapped.root) == (owners.SUPPLIED, str(root))
    assert status(project, "secret", Supply()).status == owners.UNAVAILABLE


def test_a_private_design_is_supplied_like_any_other(project, tmp_path):
    '''Surface D299: *designs can have private data for the same reason* --
    supplied from the operator's copy, and refused in the same words as any
    other private dataroot where the server has none.'''
    (tmp_path / "top.v").write_text("module top; endmodule\n")
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("mine", f"file+private://{tmp_path}")
    with design.active_dataroot("mine"), design.active_fileset("rtl"):
        design.add_file("top.v")
    mine = ("library", "gcd", "dataroot", "mine")

    def entry(supply):
        found, = [one for one in owners.account(project, "none", supply)
                  if one.dataroot == "mine"]
        return found

    assert entry(Supply(private={mine: str(tmp_path)})).status == owners.SUPPLIED
    missing = entry(Supply())
    assert missing.status == owners.UNAVAILABLE
    assert missing.why.startswith("a private dataroot this server has no copy of, and "
                                  "cannot fetch either")
    assert decide(project, ("library", "gcd", "fileset", "rtl", "file", "verilog")) != \
        (owners.PRIVATE, True)


def test_a_path_escaping_a_supplied_root_is_refused(project, tmp_path):
    root = tmp_path / "operator-copy"
    root.mkdir()
    pdk = private(PDK, "secret", "/anywhere")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "../../etc/passwd")
    project.set_pdk(pdk)

    secret = ("library", "secret", "dataroot", "secret")
    entry = status(project, "secret", Supply(private={secret: str(root)}))
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
    hashed = collected_path(project, ("library", "mine", *DATASHEET))
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
    assert read()["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "mine", "dataroot", "mine"]}]
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
        "library": {"secret": {"secret": str(root)}}}

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
    # The upload's copy: the design's dataroot rebuilt under the job, where
    # the run finds its files by path.
    from siliconcompiler.remote.server.running import runspec

    uploaded = ran.get("library", "gcd", "dataroot", "gcd-pytest-example", "path")
    assert f"/{runspec.UPLOADS_DIRNAME}/" in uploaded
    assert ran.find_files("library", "gcd", "fileset", "rtl", "file", "verilog")[0] \
        .startswith(uploaded)


@pytest.mark.parametrize("key", [
    ("library", "default", "fileset", "rtl", "file", "verilog"),
    ("history", "job0", "option", "builddir"),
    ("option", "credentials"),
    ("tool", "openroad", "task", "place", "output", "place", "0"),
    ("library", "gcd", "fileset", "rtl", "file", "verilog"),
    ("tool", "openroad", "task", "place", "script"),
])
def test_what_is_skipped_is_what_collect_leaves_out(key):
    '''🔴 One rule at both ends (it was CORE-FOLLOWUPS item 6): the client's copy had
    drifted, keeping a template's `default` keypath the collection drops.'''
    from siliconcompiler.utils.curation import filter_collection_keys

    assert owners.skipped(key) == (filter_collection_keys([(key, None, None)]) == [])


###########################
# A dataroot is named by its keypath (surface D298)
###########################

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
    rtl = ("library", "gcd", "fileset", "rtl", "file", "verilog")
    dataroot = first(project, rtl).get(field="dataroot")

    assert owners.dataroot_keypath(project, rtl, dataroot) == \
        ("library", "gcd", "dataroot", dataroot)
    assert owners.dataroot_keypath(project, ("tool", "acme_sim", "task", "run", "refdir"),
                                   "scripts") == RUN
    # No dataroot, or one its owner does not define: local, and uploaded.
    assert owners.dataroot_keypath(project, rtl, None) is None
    assert owners.dataroot_keypath(project, rtl, "nowhere") is None
    assert {one.keypath for one in owners._values(project) if one.key == rtl} == \
        {("library", "gcd", "dataroot", dataroot)}


def test_two_tasks_of_one_tool_are_two_dataroots(gcd_design):
    '''🔴 The collision `name` and `dataroot` made: a task's dataroot was named
    by its tool, so two tasks' `scripts` were one entry. Each is its own, with
    its own source -- and asked for one, the client collects that one alone.'''
    from pytasks import AcmeCheck, AcmeRun

    project = acme_project(gcd_design)

    listed = {tuple(item["keypath"]): item["source"] for item in owners.sources(project)}
    assert listed == {RUN: AcmeRun.SOURCE, CHECK: AcmeCheck.SOURCE}

    picked = owners.collection(project, lambda one: one.keypath == RUN)
    assert [key for key, _, _ in picked.keys] == [("tool", "acme_sim", "task", "run", "refdir")]


def test_a_library_and_a_tool_of_one_name_do_not_collide(gcd_design):
    project = acme_project(gcd_design)
    project.set_pdk(resource(PDK, "acme_sim", "https://github.com/siliconcompiler/acme/",
                             create=False))
    library = ("library", "acme_sim", "dataroot", "acme_sim")

    assert {tuple(item["keypath"]) for item in owners.sources(project)} == \
        {library, RUN, CHECK}
    # The server's accounting keeps them apart too: three dataroots to ask for.
    asked = [entry.wire for entry in owners.account(project, "none", Supply())
             if entry.origin == owners.REMOTE]
    assert sorted(tuple(item["keypath"]) for item in asked) == sorted([library, RUN, CHECK])


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


def test_the_run_points_each_tasks_dataroot_at_its_own_copy(gcd_design, tmp_path):
    '''The runner's half (`runspec.point_dataroots`): by the dataroot's own
    keypath, so a tool's two tasks are pointed apart -- never both at whichever
    copy came first.'''
    from siliconcompiler.remote.server.running import runspec

    project = acme_project(gcd_design)
    targets = runspec.dataroot_targets([
        owners.Entry("tool", "acme_sim", "scripts", owners.SUPPLIED,
                     root=str(tmp_path / "run"), keypath=RUN),
        owners.Entry("tool", "acme_sim", "scripts", owners.SUPPLIED,
                     root=str(tmp_path / "check"), keypath=CHECK),
        owners.Entry("design", "gcd", None, owners.UPLOADED)], tmp_path / "collection")

    assert runspec.point_dataroots(project, targets) == 2
    assert project.get(*RUN, "path") == str(tmp_path / "run")
    assert project.get(*CHECK, "path") == str(tmp_path / "check")


@pytest.mark.parametrize("collects", [False, True], ids=["as-run", "collected-again"])
def test_an_uploaded_file_is_found_by_the_run_once_its_dataroot_is_pointed(tmp_path, collects):
    '''🔴 The runner's half end to end: collected as the client collects it,
    pointed as the runner points it, and found -- where the run collects again
    before it starts, as a Slurm-dispatched one does, as well. A collected
    file is filed by its dataroot's `collection_id`, a hash of the source the
    runner then points elsewhere, so it is found at the rebuilt dataroot
    instead, never at the submitter's path.'''
    from siliconcompiler import Design, Lint
    from siliconcompiler.remote.server.running import runspec
    from siliconcompiler.schema import BaseSchema
    from siliconcompiler.utils.curation import collect

    source = tmp_path / "submitter" / "top"
    (source / "rtl").mkdir(parents=True)
    (source / "rtl" / "top.v").write_text("module top; endmodule\n")
    design = Design("top")
    design.set_dataroot("top", str(source))
    design.set_topmodule("top", fileset="rtl")
    design.add_file("rtl/top.v", dataroot="top", fileset="rtl")
    project = Lint(design)
    project.add_fileset("rtl")

    tree = tmp_path / "job" / "top" / "job0"
    collection = tree / "sc_collected_files"
    chosen = owners.collection(project, lambda one: owners.uploads(
        project, one.key, one.dataroot, one.resolvers, one.value.get()))
    collect(project, keys=chosen.keys, directory=str(collection), verbose=False,
            select=chosen.select)
    project.write_manifest(str(tree / "top.pkg.json"))
    # Nothing the run does may reach the submitter's copy.
    shutil.rmtree(tmp_path / "submitter")

    run = Lint.from_manifest(filepath=str(tree / "top.pkg.json"))
    keypath = ("library", "top", "dataroot", "top")
    targets = runspec.dataroot_targets(
        [owners.Entry("design", "top", "top", owners.UPLOADED, keypath=keypath)], collection)
    assert runspec.point_dataroots(run, targets) == 1
    assert run.get(*keypath, "path").startswith(str(tmp_path / "job" / "sc-server-uploads"))
    if collects:
        collect(run, keys=[(("library", "top", "fileset", "rtl", "file", "verilog"),
                            None, None)], verbose=False)

    found = BaseSchema._find_files(run, "library", "top", "fileset", "rtl", "file", "verilog",
                                   collection_dir=str(collection))

    assert len(found) == 1 and found[0].startswith(str(tmp_path / "job"))
    with open(found[0]) as f:
        assert f.read() == "module top; endmodule\n"


def test_a_queried_dataroots_upload_is_found_from_the_masked_manifest(tmp_path, monkeypatch):
    '''🔴 What was CORE-FOLLOWUPS item 14, end to end. A design's dataroot on a tokened
    source always uploads; the client collects it under the source as it
    registered it, and sends the manifest with the token masked. The server
    reads that manifest, and finds the upload where it arrived -- from the
    masked source alone (#5471) -- and so does the run.'''
    from siliconcompiler import Design, Lint
    from siliconcompiler.package.https import HTTPResolver
    from siliconcompiler.remote.server.running import runspec
    from siliconcompiler.schema import BaseSchema
    from siliconcompiler.utils.curation import collect

    fetched = tmp_path / "fetched"
    (fetched / "rtl").mkdir(parents=True)
    (fetched / "rtl" / "top.v").write_text("module top; endmodule\n")
    # The download, on the client: no network here.
    monkeypatch.setattr(HTTPResolver, "resolve", lambda self: str(fetched))

    design = Design("top")
    design.set_dataroot("top", "https://example.com/ip/archive/?token=SECRET", tag="v1")
    design.set_topmodule("top", fileset="rtl")
    design.add_file("rtl/top.v", dataroot="top", fileset="rtl")
    project = Lint(design)
    project.add_fileset("rtl")

    tree = tmp_path / "job" / "top" / "job0"
    collection = tree / "sc_collected_files"
    chosen = owners.collection(project, lambda one: owners.uploads(
        project, one.key, one.dataroot, one.resolvers, one.value.get()))
    collect(project, keys=chosen.keys, directory=str(collection), verbose=False,
            select=chosen.select)
    owners.without_credentials(project).write_manifest(str(tree / "top.pkg.json"))
    assert "SECRET" not in (tree / "top.pkg.json").read_text()

    # The server's half: the manifest as sent, and nothing fetched.
    monkeypatch.setattr(HTTPResolver, "resolve",
                        lambda self: pytest.fail("the server fetched a masked source"))
    run = Lint.from_manifest(filepath=str(tree / "top.pkg.json"))
    keypath = ("library", "top", "dataroot", "top")
    record, = [one for one in owners.value_records(run, str(collection))
               if one["key"][:2] == ["library", "top"]]
    assert record["collected"], "the upload is not where the masked manifest looks"

    targets = runspec.dataroot_targets(
        [owners.Entry("design", "top", "top", owners.UPLOADED, keypath=keypath)], collection)
    assert runspec.point_dataroots(run, targets) == 1
    found, = BaseSchema._find_files(run, "library", "top", "fileset", "rtl", "file", "verilog",
                                    collection_dir=str(collection))
    with open(found) as f:
        assert f.read() == "module top; endmodule\n"


def test_a_private_dataroot_is_supplied_by_the_first_of_three_and_never_asked_for(
        project, tmp_path):
    '''Surface D299: the operator's copy, then a copy of its source this
    server holds, then a fetch from the allowlist -- and UNAVAILABLE where none
    answers, never ASK.'''
    source = "https://github.com/siliconcompiler/secret/archive/"
    pdk = PDK("secret")
    pdk.set_dataroot("secret", source.replace("https", "https+private", 1), tag="v1")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    project.set_pdk(pdk)
    keypath = ("library", "secret", "dataroot", "secret")
    (tmp_path / "datasheet.pdf").write_text("x")
    record, = [one for one in owners.value_records(project, "none")
               if one["key"][:2] == ["library", "secret"]]

    # The manifest's own source, masked as any source is, and never uploaded.
    assert (record["origin"], record["source"], record["ref"]) == \
        (owners.PRIVATE, source, "v1")
    assert decide(project, ("library", "secret", *DATASHEET)) == (owners.PRIVATE, False)

    def status(supply):
        entry, = [one for one in owners.account(project, "none", supply)
                  if one.keypath == keypath]
        return entry.status

    held = Supply(held={(source, "v1"): str(tmp_path)})
    assert status(Supply(private={keypath: str(tmp_path)}, allowed=[source])) == \
        owners.SUPPLIED
    assert status(held) == owners.SUPPLIED
    assert status(Supply(allowed=[source])) == owners.FETCH
    assert status(Supply()) == owners.UNAVAILABLE
