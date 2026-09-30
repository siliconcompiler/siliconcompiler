import importlib.util
import os

import pytest


# `setup/server/bootstrap.py` runs as a compose service and had no tests. Two
# real bugs came out of it in one afternoon -- a `Cmd` that never ran because
# the image has an ENTRYPOINT, and a loop variable that shadowed the
# SiliconCompiler version -- and both were found by a person bringing the
# stack up rather than by anything here.
#
# It is loaded by path because it is a script beside a Dockerfile and not part
# of the package.

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(HERE, "setup", "server", "bootstrap.py")


@pytest.fixture
def bootstrap(monkeypatch):
    spec = importlib.util.spec_from_file_location("sc_bootstrap", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Nothing reaches the docker socket or the registry command.
    module.calls = []
    monkeypatch.setattr(module, "registry",
                        lambda *args: module.calls.append(list(args)))
    monkeypatch.setattr(module, "say", lambda message: None)
    # `built_at` reads the image off the daemon, which nothing here has.
    monkeypatch.setattr(module, "built_at",
                        lambda image: "2026-09-24T10:11:12.000000000Z")
    return module


def commands(module, name):
    return [call for call in module.calls if call and call[0] == name]


def test_the_images_are_tagged_with_the_siliconcompiler_version(bootstrap):
    """🔴 The regression this file exists for. A loop binding each tool's
    version to `version` shadowed the parameter, so both images were tagged
    with whatever the LAST tool reported -- `19.1.5`, which is mlir's -- and
    declared to contain `siliconcompiler==19.1.5`. The server then refused to
    start, correctly, saying it could not read a siliconcompiler nobody had
    asked it to.
    """
    held = {tool: {"kind": "tool", "version": f"{n}.0", "present": True}
            for n, tool in enumerate(bootstrap.TOOLS)}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                       held, {})

    refs = [call[1] for call in commands(bootstrap, "add-image")]
    assert refs == [f"{bootstrap.PULL_FROM}/sc-runtime:0.38.9",
                    f"{bootstrap.PULL_FROM}/sc-tools:0.38.9"]

    for call in commands(bootstrap, "add-image"):
        assert "siliconcompiler==0.38.9" in call


def test_a_tool_that_reported_is_registered_as_reported(bootstrap):
    held = {"yosys": {"kind": "tool", "version": "0.69", "present": True}}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                       held, {})

    added = [call for call in commands(bootstrap, "add-version")
             if call[1] == "yosys"]
    assert added == [["add-version", "yosys", "0.69"]]


def test_a_tool_that_said_nothing_gets_the_publish_date_and_the_mark(bootstrap):
    """🔴 `20260924` beats `2.0.1` under every comparison there is, so an
    unmarked date would outrank every real release for ever.

    ⚠️ Present and silent, which is what that value is for. A tool the probe
    did not SEE declares nothing at all."""
    held = {tool: {"kind": "tool", "version": None, "present": True}
            for tool in bootstrap.TOOLS}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", held, {})

    for tool in bootstrap.TOOLS:
        assert ["add-version", tool, "20260924", "-unversioned"] in bootstrap.calls


def test_every_tool_records_the_driver_the_table_names(bootstrap):
    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", {}, {})

    added = {call[1]: call for call in commands(bootstrap, "add-software")}
    assert added["openroad"][-2:] == ["-driver",
                                      "siliconcompiler.tools.openroad"]
    # And every tool says its kind, because the kind is stated and never
    # derived.
    assert added["openroad"][2:4] == ["-kind", "tool"]
    assert added["siliconcompiler"][2:4] == ["-kind", "python"]


def test_the_image_declares_what_the_probe_found(bootstrap):
    """What goes in `-contains` is the version that was registered, or the
    registry refuses a version it just accepted."""
    held = {"yosys": {"kind": "tool", "version": "0.69", "present": True},
            "openroad": {"kind": "tool", "version": None, "present": True},
            "magic": {"kind": "tool", "version": None, "present": False}}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", held, {})

    tools = commands(bootstrap, "add-image")[-1]
    assert "yosys==0.69" in tools
    # Present and silent falls back to the date; not there declares nothing.
    assert "openroad==20260924" in tools
    assert not [arg for arg in tools if arg.startswith("magic==")]


def test_the_catalogue_is_spelled_out_and_the_modules_import(bootstrap):
    """🔴 Spelled out rather than worked out, because there is no convention to
    fall back on: `kepler-formal` is driven from
    `siliconcompiler.tools.keplerformal`, so `siliconcompiler.tools.<name>` is
    already wrong in this tree. A default that is right most of the time gets
    trusted and is wrong exactly where nobody is looking.

    ⚠️ What a table cannot do is go stale quietly, so this checks every entry
    against the tree it names.
    """
    import importlib

    assert bootstrap.DRIVERS["kepler-formal"] == \
        "siliconcompiler.tools.keplerformal"

    for tool, module in bootstrap.DRIVERS.items():
        importlib.import_module(module)

    # 🔴 And neither is in it, because the TASKS say so rather than a list
    # here: a join runs in SiliconCompiler's process, and an execute task's
    # command comes out of the manifest.
    assert "builtin" not in bootstrap.DRIVERS
    assert "execute" not in bootstrap.DRIVERS


def test_the_catalogue_covers_every_tool_siliconcompiler_drives(bootstrap):
    """The table is the catalogue, so a tool added to the tree and not to it
    is one a flow can reach for and this deployment will refuse by name.

    ⚠️ Which is right when it is deliberate -- `vivado` is not shipped here --
    and a bug when a tool was simply forgotten. `NOT_PUBLISHED` is what tells
    the two apart, and this fails if a new tool appears in neither."""
    import importlib
    import pkgutil

    import siliconcompiler.tools
    from siliconcompiler import Task

    for found in pkgutil.walk_packages(siliconcompiler.tools.__path__,
                                       prefix="siliconcompiler.tools."):
        try:
            importlib.import_module(found.name)
        except Exception:                                        # noqa: BLE001
            continue

    def descendants(cls):
        for child in cls.__subclasses__():
            yield child
            yield from descendants(child)

    declared = set()
    for task_cls in set(descendants(Task)):
        # ⚠️ Shipped drivers only. Every Task subclass this interpreter has
        # ever imported is reachable from here, and a test file two directories
        # away that defines one for its own purposes is not a tool anybody
        # deploys -- without this the check passes or fails on test order.
        if not (task_cls.__module__ or "").startswith("siliconcompiler.tools."):
            continue
        try:
            wanted = task_cls()._remote_toolname
        except Exception:                                        # noqa: BLE001
            continue
        if wanted:
            declared.add(wanted)

    # ⚠️ Against the deliberate omissions, not against nothing: a tool left
    # out on purpose and one forgotten look identical otherwise, and only the
    # second is a bug.
    assert declared - set(bootstrap.DRIVERS) == bootstrap.NOT_PUBLISHED
    assert not (set(bootstrap.DRIVERS) & bootstrap.NOT_PUBLISHED)


def test_main_tags_and_registers_with_the_siliconcompiler_version(bootstrap,
                                                                  monkeypatch):
    """🔴 The same shadowing happened twice -- once in `register` and once in
    `main`'s own logging loop -- and both times both images were tagged with
    whatever the LAST tool reported. This covers the outer scope, which the
    `register` test cannot: `main` is where the version is read and where it
    is handed to `push`.
    """
    import siliconcompiler

    pushed, registered = [], []

    monkeypatch.setattr(bootstrap, "wait_for_registry", lambda: None)
    monkeypatch.setattr(bootstrap, "write_config", lambda: None)
    monkeypatch.setattr(bootstrap, "already_registered", lambda version: False)
    monkeypatch.setattr(bootstrap, "published_on", lambda image: "20260924")
    # Every tool answers with a different version, which is what made the last
    # one win.
    monkeypatch.setattr(
        bootstrap, "ask_image",
        lambda image, python, drivers: {
            tool: {"kind": "tool", "version": f"{n}.0", "reported": f"{n}.0"}
            for n, tool in enumerate(bootstrap.TOOLS)})
    monkeypatch.setattr(
        bootstrap, "push",
        lambda local, repo, tag: pushed.append((repo, tag)) or f"sha256:{repo}")
    monkeypatch.setattr(
        bootstrap, "register",
        lambda version, *rest: registered.append(version))

    assert bootstrap.main() == 0

    assert pushed == [("sc-runtime", siliconcompiler.__version__),
                      ("sc-tools", siliconcompiler.__version__)]
    assert registered == [siliconcompiler.__version__]


def test_both_numbers_are_logged_where_they_differ(bootstrap, capsys,
                                                   monkeypatch):
    """`verilator` says 5.052 and PEP 440 stores 5.52. An operator reading the
    log is owed the first; the registry needs the second."""
    said = []
    monkeypatch.setattr(bootstrap, "say", said.append)

    bootstrap.say_what_it_holds({
        "verilator": {"version": "5.52", "reported": "5.052", "present": True},
        "yosys": {"version": "0.69", "reported": "0.69", "present": True},
        "magic": {"version": None, "reported": None, "present": False}})

    assert "  verilator: 5.52  (reported 5.052)" in said
    assert "  yosys: 0.69" in said
    # ⚠️ Silent about a tool the image does not have: the catalogue is every
    # tool SiliconCompiler drives, and most images hold a handful.
    assert not any(line.startswith("  magic:") for line in said)


def test_a_tool_whose_version_is_a_distribution_is_still_a_tool(bootstrap):
    """🔴 `slang` is a tool to a flow -- a node names it and has to be placed
    in an image holding it -- and its version is a python package, because its
    driver runs pyslang in SiliconCompiler's own process. The difference is how
    the version is read, not what it is."""
    assert bootstrap.AS_DISTRIBUTION["slang"] == "pyslang"
    assert "slang" in bootstrap.TOOLS

    bootstrap.register(
        "0.38.9", "sha256:b", "sha256:a", "20260924",
        {"slang": {"kind": "tool", "version": "11.0.0", "present": True}}, {})

    added = {call[1]: call for call in commands(bootstrap, "add-software")}
    assert added["slang"][2:4] == ["-kind", "tool"]
    assert ["add-version", "slang", "11.0.0"] in bootstrap.calls


def test_cocotb_is_registered_and_declared_where_it_was_found(bootstrap):
    """🔴 A cocotb node's `requested_versions.python` names cocotb at SiliconCompiler's
    range, so an image holding it says so -- and one the probe found without
    it declares nothing."""
    bootstrap.register(
        "0.38.9", "sha256:b", "sha256:a", "20260924",
        {"cocotb": {"kind": "python", "version": "2.1.3", "present": True}},
        {"cocotb": {"kind": "python", "version": None, "present": False}})

    added = {call[1]: call for call in commands(bootstrap, "add-software")}
    assert added["cocotb"][2:4] == ["-kind", "python"]
    images = {call[1].split("/")[-1].split(":")[0]: call
              for call in commands(bootstrap, "add-image")}
    assert "cocotb==2.1.3" in images["sc-tools"]
    assert "cocotb==2.1.3" not in images["sc-runtime"]


def test_each_image_declares_only_what_the_probe_found_in_it(bootstrap):
    """⚠️ Every tool in the catalogue is asked of every image, and most images
    hold a handful. Declaring one that is not there is the claim that gets a
    node dispatched into a container without it -- and `slang` is why the small
    image declares anything at all: it arrives with siliconcompiler rather than
    with the EDA stack."""
    bootstrap.register(
        "0.38.9", "sha256:b", "sha256:a", "20260924",
        {"openroad": {"kind": "tool", "version": "26.3", "present": True},
         "slang": {"kind": "tool", "version": "11.0.0", "present": True}},
        {"slang": {"kind": "tool", "version": "11.0.0", "present": True}})

    runtime, tools = commands(bootstrap, "add-image")

    assert "slang==11.0.0" in runtime
    assert not [arg for arg in runtime if arg.startswith("openroad==")]

    assert "openroad==26.3" in tools
    assert "slang==11.0.0" in tools
    # And nothing for the twenty-nine the probe did not see.
    assert not [arg for arg in tools if arg.startswith("magic==")]


def test_built_at_is_a_timestamp_and_not_the_publish_date(bootstrap):
    """🔴 They are not the same thing. The date is a VERSION for a tool that
    reports none, so it has to compare as a version; `built_at` breaks the tie
    between two images carrying identical versions -- and two images built on
    the same day is the ordinary case, so a date cannot break it."""
    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", {}, {})

    for call in commands(bootstrap, "add-image"):
        built = call[call.index("-built") + 1]
        assert built.startswith("2026-09-24T")
        assert built != "20260924"


def test_an_image_missing_a_tool_it_would_claim_is_refused(bootstrap):
    """🔴 The WHOLE image, not just that row. Writing the row says the image
    holds something it does not -- and then a node is placed in it,
    dispatched, and dies with every other node cancelled behind it. That is
    the `bsc` failure moved one step earlier, which is where it is cheap."""
    held = {tool: {"kind": "tool", "version": "1.0", "present": True}
            for tool in bootstrap.TOOLS}
    held["openroad"] = {"kind": "tool", "version": None, "present": False}

    with pytest.raises(SystemExit, match="does not hold openroad"):
        bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                           held, {})

    assert not commands(bootstrap, "add-image")


def test_present_but_silent_is_registered_rather_than_refused(bootstrap):
    """✅ Legitimate, and it is what `published_date` exists for."""
    held = {tool: {"kind": "tool", "version": None, "present": True}
            for tool in bootstrap.TOOLS}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", held, {})

    assert ["add-version", "openroad", "20260924", "-unversioned"] \
        in bootstrap.calls
    assert commands(bootstrap, "add-image")


def test_a_tool_nobody_drives_cannot_be_tested_and_is_not_refused(bootstrap):
    """⚠️ Untestable is not absent. Only a check that RAN and said no is
    grounds to refuse an image."""
    held = {tool: {"kind": "tool", "version": None, "present": None}
            for tool in bootstrap.TOOLS}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", held, {})

    # Not refused -- and declared by nothing either, because a row is a claim
    # the image holds it and nobody checked.
    images = commands(bootstrap, "add-image")
    assert images
    assert not [arg for arg in images[-1] if arg.startswith("openroad==")]


def test_a_tool_read_through_a_distribution_records_it(bootstrap):
    """🔴 Handed to the probe rather than worked out there: `slang`'s version
    is `pyslang`'s, and the distribution is not called what the tool is."""
    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", {}, {})

    added = {call[1]: call for call in commands(bootstrap, "add-software")}
    assert added["slang"][-2:] == ["-version-package", "pyslang"]
    assert "-version-package" not in added["openroad"]


def test_a_version_that_did_not_parse_lands_on_the_publish_date(bootstrap):
    """🔴 What the probe could not parse is registered as present and mute --
    never as `reported`, which the store refuses, and never coerced."""
    held = {tool: {"kind": "tool", "version": None, "present": True}
            for tool in bootstrap.TOOLS}
    held["gtkwave"]["unparsed"] = "initialize"

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", held, {})

    assert ["add-version", "gtkwave", "20260924", "-unversioned"] \
        in bootstrap.calls
    assert not any("initialize" in call for call in bootstrap.calls)


def test_a_version_that_did_not_parse_is_said(bootstrap, monkeypatch):
    said = []
    monkeypatch.setattr(bootstrap, "say", said.append)

    bootstrap.say_what_it_holds({
        "gtkwave": {"version": None, "reported": "initialize",
                    "unparsed": "initialize", "present": True}})

    assert any("gtkwave" in line and "'initialize' is not a version" in line
               for line in said)


######################################################################
# Nothing to do when nothing changed
######################################################################

def digest(letter):
    return "sha256:" + letter * 64


def pushed(bootstrap, monkeypatch, runtime, tools):
    """The daemon, answering for two images pushed as these digests. None is
    an image that was never pushed: a rebuild that changed something."""
    local = {bootstrap.RUNTIME_IMAGE: ("sc-runtime", runtime),
             bootstrap.STACK_IMAGE: ("sc-tools", tools)}

    def get(path):
        repository, pushed_as = local[path.split("/")[2]]
        # Compose's own name is in there too, and is not a push.
        refs = [f"{path.split('/')[2]}@{digest('f')}"]
        if pushed_as:
            refs.append(f"{bootstrap.PUSH_TO}/{repository}@{pushed_as}")
        return {"RepoDigests": refs}

    monkeypatch.setattr(bootstrap, "_get", get)


def registered(bootstrap, monkeypatch, version, runtime, tools, staged=True):
    """A store holding both images live at `version`, as a finished bootstrap
    leaves it."""
    from pathlib import Path
    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.state.store import Store

    monkeypatch.setattr(bootstrap, "DATADIR", Path("sc_server").resolve())

    with Store(bootstrap.DATADIR / "server.db") as store:
        with store.transaction():
            actor = store.upsert_user("operator", "someone@host")["id"]
        images.register_software(store, "siliconcompiler", "SiliconCompiler",
                                 actor, "python")
        images.register_version(store, "siliconcompiler", version, actor)
        for repository, image in (("sc-runtime", runtime), ("sc-tools", tools)):
            images.register_image(
                store, f"{bootstrap.PULL_FROM}/{repository}:{version}", image,
                [("siliconcompiler", version)], actor)

            if staged:
                bundle = images.bundle_path(bootstrap.DATADIR / "images", image)
                bundle.mkdir(parents=True)
                (bundle / "config.json").write_text("{}")


def test_an_image_already_registered_and_staged_is_left_alone(
        bootstrap, monkeypatch):
    registered(bootstrap, monkeypatch, "0.38.9", digest("a"), digest("b"))
    pushed(bootstrap, monkeypatch, runtime=digest("a"), tools=digest("b"))

    assert bootstrap.already_registered("0.38.9")


@pytest.mark.parametrize("version,runtime,tools,staged", [
    # Rebuilt: the image under that name was never pushed.
    ("0.38.9", digest("a"), None, True),
    # Pushed, but the store holds a different build at that reference.
    ("0.38.9", digest("a"), digest("c"), True),
    # A new SiliconCompiler version is a new reference.
    ("0.39.0", digest("a"), digest("b"), True),
    # Registered and never unpacked.
    ("0.38.9", digest("a"), digest("b"), False),
])
def test_anything_short_of_that_is_registered_again(bootstrap, monkeypatch,
                                                    version, runtime, tools,
                                                    staged):
    registered(bootstrap, monkeypatch, "0.38.9", digest("a"), digest("b"),
               staged=staged)
    pushed(bootstrap, monkeypatch, runtime=runtime, tools=tools)

    assert not bootstrap.already_registered(version)


def test_no_store_is_not_registered_and_is_not_created(bootstrap, monkeypatch):
    """⚠️ Asking must not write. A fresh deployment's store is created by the
    first registry command, not by the check that decides whether to run it."""
    from pathlib import Path

    monkeypatch.setattr(bootstrap, "DATADIR", Path("sc_server").resolve())
    pushed(bootstrap, monkeypatch, runtime=digest("a"), tools=digest("b"))

    assert not bootstrap.already_registered("0.38.9")
    assert not (bootstrap.DATADIR / "server.db").exists()


def test_main_neither_probes_nor_pushes_what_is_already_registered(
        bootstrap, monkeypatch):
    """🔴 The point of the check: every `docker compose up` used to probe both
    images, push both and re-register both, to write rows already there."""
    def refuse(*args, **kwargs):
        raise AssertionError("bootstrap did work there was no need for")

    monkeypatch.setattr(bootstrap, "wait_for_registry", lambda: None)
    monkeypatch.setattr(bootstrap, "write_config", lambda: None)
    monkeypatch.setattr(bootstrap, "already_registered", lambda version: True)
    for step in ("published_on", "ask_image", "push", "register"):
        monkeypatch.setattr(bootstrap, step, refuse)

    assert bootstrap.main() == 0


def on_containerd(bootstrap, monkeypatch, runtime, tools):
    """The containerd image store: the ID is an index whose digest changes on
    every build, because the attestation in it carries the build's time, and
    the image's own manifest is listed beside that attestation."""
    local = {bootstrap.RUNTIME_IMAGE: runtime, bootstrap.STACK_IMAGE: tools}

    def get(path):
        assert path.endswith("?manifests=1"), path
        return {
            # Never pushed under this ID: every build is a new one.
            "Id": digest("e"), "RepoDigests": [],
            "Manifests": [
                {"Kind": "image",
                 "Descriptor": {"digest": local[path.split("/")[2]]},
                 "ImageData": {"Platform": {"os": "linux", "architecture": "amd64"}}},
                {"Kind": "attestation", "Descriptor": {"digest": digest("d")}}]}

    monkeypatch.setattr(bootstrap, "_get", get)


def test_a_rebuild_that_changed_nothing_is_still_registered(bootstrap, monkeypatch):
    """🔴 The case the image ID gets wrong. Every layer a cache hit, and still
    a new ID and a new pushed digest -- so every `docker compose up` pushed
    and registered both images again. The image's own manifest did not move."""
    registered(bootstrap, monkeypatch, "0.38.9", digest("a"), digest("b"))
    on_containerd(bootstrap, monkeypatch, runtime=digest("a"), tools=digest("b"))

    assert bootstrap.already_registered("0.38.9")


def test_a_rebuild_that_changed_the_image_is_registered_again(bootstrap, monkeypatch):
    registered(bootstrap, monkeypatch, "0.38.9", digest("a"), digest("b"))
    on_containerd(bootstrap, monkeypatch, runtime=digest("a"), tools=digest("c"))

    assert not bootstrap.already_registered("0.38.9")


def test_only_the_images_own_manifest_is_pushed(bootstrap, monkeypatch):
    """So the digest the registry reports -- and the one registered -- is the
    one `already_registered` compares, not the index around it."""
    on_containerd(bootstrap, monkeypatch, runtime=digest("a"), tools=digest("b"))

    posted = []

    def post(path, headers=None):
        posted.append(path)
        if "/push?" in path:
            return [{"status": f"0.38.9: digest: {digest('a')} size: 2008"}]
        return {}

    monkeypatch.setattr(bootstrap, "_post", post)

    assert bootstrap.push(bootstrap.RUNTIME_IMAGE, "sc-runtime", "0.38.9") == digest("a")

    pushes = [path for path in posted if "/push?" in path]
    assert len(pushes) == 1
    import json
    import urllib.parse
    platform = urllib.parse.parse_qs(urllib.parse.urlsplit(pushes[0]).query)["platform"]
    assert json.loads(platform[0]) == {"os": "linux", "architecture": "amd64"}


def test_the_classic_store_pushes_the_whole_image(bootstrap, monkeypatch):
    """No index there, so nothing to choose between -- and no platform to
    send."""
    pushed(bootstrap, monkeypatch, runtime=None, tools=None)

    posted = []
    monkeypatch.setattr(bootstrap, "_post", lambda path, headers=None: posted.append(path) or (
        [{"status": f"t: digest: {digest('a')} size: 1"}] if "/push?" in path else {}))

    bootstrap.push(bootstrap.RUNTIME_IMAGE, "sc-runtime", "0.38.9")

    assert not any("platform=" in path for path in posted)
