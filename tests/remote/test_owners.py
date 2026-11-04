import json
import os
import sys

import pytest

from siliconcompiler import ASIC, PDK, StdCellLibrary
from siliconcompiler.remote import owners


# What goes in a remote run's archive.

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
    for one in owners.walk(project):
        if one.key == tuple(key) and one.value.get() == path:
            return owners.collected_path(one)
    raise AssertionError(f"{key} has no value {path}")


def decide(project, key, n=0):
    '''What `collect`'s selector is asked about the ``n``th value: its source,
    and whether it goes up.'''
    ones = [one for one in owners.walk(project) if one.key == tuple(key)]
    # What is never walked is never collected.
    return (ones[n].origin, ones[n].upload) if ones else (None, False)


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
    # The server never expands a variable, so the client does, with its own
    # environment, and uploads what it finds.
    ("$FOUNDRY_ROOT", False, owners.LOCAL, True),
    ("dataroot://real", False, owners.REMOTE, False),       # judged by the one it names
    # No server lists a package nothing provides, so its files go up.
    ("python://some_pdk_package", False, owners.INSTALLED, True),
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
    # No distribution provides the module, so no server supplies it by version.
    assert {(one.keypath, one.distribution) for one in owners.walk(project)
            if one.origin == owners.INSTALLED} == \
        ({(("library", "mypdk", "dataroot", "mypdk"), None)} if origin == owners.INSTALLED
         else set())


def test_finding_a_tests_collected_path_fetches_nothing(project, tmp_path, monkeypatch):
    '''Only a value that goes up is resolved: a remote PDK is not fetched to
    find where the design's own file lands.'''
    from siliconcompiler.package.https import HTTPResolver

    monkeypatch.setattr(HTTPResolver, "get_path", lambda self: pytest.fail("fetched"))
    project.set_pdk(resource(PDK, "mypdk", "https://example.test/pdk.tar.gz", create=False))
    path = project.find_files(*RTL)[0]

    found = owners.collected_paths(list(owners.walk(project)), [path])

    assert found == {path: collected_path(project, RTL)}


@pytest.mark.parametrize("scheme", [
    "file+private", "git+private", "git+https+private", "git+ssh+private",
    "ssh+private", "http+private", "https+private"])
def test_every_private_scheme_is_private_before_any_other_rule(project, tmp_path, scheme):
    '''A `+private` suffix on any scheme: never uploaded, even from
    this disk; a remote one sends its cleaned source and ref, a local none.'''
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
    entry, = [item for item in owners.sources(owners.walk(project))
              if item["keypath"] == ["library", "secret", "dataroot", "secret"]]
    assert entry["private"] is True
    if local:
        assert "source" not in entry and "ref" not in entry
        assert str(tmp_path) not in json.dumps(entry)
    else:
        assert entry["source"].endswith("://host/secret.git?k=***") and entry["ref"] == "v1"
        assert "ghp_TOKEN" not in entry["source"] and "alice" not in entry["source"]


def test_sources_name_what_is_not_uploaded_as_both_ends_read_it_without_a_credential(
        project, tmp_path):
    '''`safe_source` (#5454): no userinfo, every query value masked -- one
    string in the client's `sources`. A design's own remote dataroot goes up,
    so it is not listed.'''
    project.set_pdk(resource(
        PDK, "lambda", "https://user:ghp_x@github.com/siliconcompiler/x/archive/v1.tar.gz"
        "?access_token=SECRET&lfs=true", create=False))
    project.add_asiclib(private(StdCellLibrary, "secretlib", tmp_path))
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("ip", GITHUB, "v1")
    with design.active_dataroot("ip"):
        design.add_file("ip.v", fileset="rtl")

    listed = {tuple(item["keypath"]): item for item in owners.sources(owners.walk(project))}

    assert not any("kind" in item for item in listed.values())       # by keypath
    assert not any(keypath[1] == "gcd" for keypath in listed)
    sent = listed[("library", "lambda", "dataroot", "lambda")]
    assert sent["source"] == ("https://github.com/siliconcompiler/x/archive/v1.tar.gz"
                              "?access_token=***&lfs=***")
    assert (sent["ref"], sent["private"]) == ("v1", False)
    hidden = listed[("library", "secretlib", "dataroot", "secretlib")]
    assert hidden["private"] is True and "source" not in hidden


@pytest.mark.parametrize("url,sent", [
    ("git+https://alice:TOKEN@example.com/ip.git", "git+https://example.com/ip.git"),
    ("git+ssh://git@github.com/acme/ip.git", "git+ssh://github.com/acme/ip.git"),
    ("https://TOKEN@example.com/x", "https://example.com/x"),
    ("git+https://example.com/ip.git@v1", "git+https://example.com/ip.git@v1"),
    ("/home/me@corp/ip", "/home/me@corp/ip"),
])
def test_a_masked_url_loses_what_is_ahead_of_the_host_and_keeps_its_path(url, sent):
    '''What the client strips and the server refuses: `git@` included.'''
    assert owners.masked(url) == sent


def uploaded_by_owner(project):
    '''What a remote run hands `collect`, by the owner rule alone.'''
    return owners.collection(owners.walk(project), lambda one: one.upload)


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
def test_a_file_with_many_names_is_reported_once():
    '''Stored once, every other name a link carrying no bytes: the report says
    what the archive holds.'''
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
    report = owners.upload_report(owners.walk(project), collection)
    assert sum(row[3] for row in report) == \
        os.path.getsize("proj/rtl/a.v") + os.path.getsize("proj/rtl/defs.vh")
    assert sum(row[4] for row in report) == 2


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
    '''A parameter may go up in part: the local value goes up, the
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
    from siliconcompiler.utils.curation import filter_collection_keys, never_collected

    assert never_collected(key) == (filter_collection_keys([(key, None, None)]) == [])


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
    assert {one.keypath for one in owners.walk(project) if one.key == RTL} == \
        {("library", "gcd", "dataroot", dataroot)}


def test_a_dataroot_no_keypath_names_stops_the_client_before_create(
        project, monkeypatch, logged_in):
    '''The server refuses a keypath of any other shape, so the client says so
    first, naming the parameter.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.remote import RemoteError
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.tools.builtin.nop import NOPTask

    project.set_pdk(resource(PDK, "lambda", "https://github.com/siliconcompiler/x/",
                             create=False))
    monkeypatch.setattr(owners, "dataroot_keypath",
                        lambda project, key, dataroot: ("elsewhere", "dataroot", dataroot))

    with pytest.raises(owners.Unnamed, match=r"\[library,lambda,package,doc,datasheet\]"):
        owners.sources(owners.walk(project))
    flow = Flowgraph("only")
    flow.node("run", NOPTask())
    project.set_flow(flow)
    run = RemoteRun(project, logged_in)
    with pytest.raises(RemoteError, match="neither a library's nor a task's"):
        run._plan(run._read())
