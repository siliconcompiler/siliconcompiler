import importlib
import importlib.util
import json
import os
import urllib.parse
from pathlib import Path

import pytest


# `setup/server/bootstrap.py`, the compose service that registers the images.
# Loaded by path: it is a script beside a Dockerfile, not part of the package.

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
    monkeypatch.setattr(module, "built_at",
                        lambda image: "2026-09-24T10:11:12.000000000Z")
    return module


def commands(module, name):
    return [call for call in module.calls if call and call[0] == name]


def register(bootstrap, held=None, runtime_held=None):
    '''`register` at SiliconCompiler 0.38.9, published 20260924.'''
    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                       held or {}, runtime_held or {})


def software(bootstrap):
    return {call[1]: call for call in commands(bootstrap, "add-software")}


def test_the_images_are_tagged_with_the_siliconcompiler_version(bootstrap):
    '''Both images are tagged with siliconcompiler's version, not the last tool's (a loop variable
    once shadowed it), and `-built` is a build timestamp, never a publish date.'''
    register(bootstrap, {tool: {"kind": "tool", "version": f"{n}.0", "present": True}
                         for n, tool in enumerate(bootstrap.TOOLS)})

    added = commands(bootstrap, "add-image")
    assert [call[1] for call in added] == [f"{bootstrap.PULL_FROM}/sc-runtime:0.38.9",
                                           f"{bootstrap.PULL_FROM}/sc-tools:0.38.9"]
    for call in added:
        assert "siliconcompiler==0.38.9" in call
        built = call[call.index("-built") + 1]
        assert built.startswith("2026-09-24T") and built != "20260924"


def test_the_image_declares_what_the_probe_found(bootstrap):
    '''Reported is registered as reported; present and silent falls back to
    the publish date, marked; not there declares nothing. `-contains` names
    the version registered, or the registry refuses one it just accepted.'''
    register(bootstrap, {"yosys": {"kind": "tool", "version": "0.69", "present": True},
                         "openroad": {"kind": "tool", "version": None, "present": True},
                         "magic": {"kind": "tool", "version": None, "present": False}})

    assert [call for call in commands(bootstrap, "add-version")
            if call[1] == "yosys"] == [["add-version", "yosys", "0.69"]]
    tools = commands(bootstrap, "add-image")[-1]
    assert "yosys==0.69" in tools
    assert "openroad==20260924" in tools
    assert not [arg for arg in tools if arg.startswith("magic==")]


def test_a_silent_or_unparsed_tool_gets_the_publish_date_and_the_mark(bootstrap):
    '''`20260924` beats `2.0.1` under every comparison, so an unmarked date
    would outrank every real release. Present and silent is registered, not
    refused; a version that did not parse lands there too and is never
    passed on (the store refuses it as `reported`).'''
    held = {tool: {"kind": "tool", "version": None, "present": True}
            for tool in bootstrap.TOOLS}
    held["gtkwave"]["unparsed"] = "initialize"

    register(bootstrap, held)

    for tool in bootstrap.TOOLS:
        assert ["add-version", tool, "20260924", "-unversioned"] in bootstrap.calls
    assert not any("initialize" in call for call in bootstrap.calls)
    assert commands(bootstrap, "add-image")


def test_every_tool_records_its_kind_and_the_driver_the_table_names(bootstrap):
    '''The kind is stated, never derived. `slang`'s version is read from
    `pyslang`, a distribution not called what the tool is, so it is handed
    to the probe.'''
    register(bootstrap)

    added = software(bootstrap)
    assert added["openroad"][2:4] == ["-kind", "tool"]
    assert added["openroad"][-2:] == ["-driver", "siliconcompiler.tools.openroad"]
    assert "-version-package" not in added["openroad"]
    assert added["siliconcompiler"][2:4] == ["-kind", "python"]
    assert added["slang"][-2:] == ["-version-package", "pyslang"]


def test_the_catalogue_is_spelled_out_and_covers_every_tool_siliconcompiler_drives(
        bootstrap):
    '''The catalogue is spelled out, since a tool's name need not match its module (`kepler-formal`
    is `tools.keplerformal`), so every entry must import. A tool missing from it is refused by name,
    and `NOT_PUBLISHED` tells a deliberate omission (`vivado`) from a forgotten one.'''
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
        # Shipped drivers only: a test's own Task subclass would make this
        # pass or fail on test order.
        if not (task_cls.__module__ or "").startswith("siliconcompiler.tools."):
            continue
        try:
            wanted = task_cls()._remote_toolname
        except Exception:                                        # noqa: BLE001
            continue
        if wanted:
            declared.add(wanted)

    assert declared - set(bootstrap.DRIVERS) == bootstrap.NOT_PUBLISHED
    assert not (set(bootstrap.DRIVERS) & bootstrap.NOT_PUBLISHED)

    assert bootstrap.DRIVERS["kepler-formal"] == "siliconcompiler.tools.keplerformal"
    for module in bootstrap.DRIVERS.values():
        importlib.import_module(module)
    assert "builtin" not in bootstrap.DRIVERS
    assert "execute" not in bootstrap.DRIVERS


def skip_the_daemon(bootstrap, monkeypatch, registered):
    monkeypatch.setattr(bootstrap, "wait_for_registry", lambda: None)
    monkeypatch.setattr(bootstrap, "write_config", lambda: None)
    monkeypatch.setattr(bootstrap, "already_registered", lambda version: registered)


def test_main_tags_and_registers_with_the_siliconcompiler_version(bootstrap,
                                                                  monkeypatch):
    '''The same shadowing happened in `main`'s own logging loop, which is
    where the version is read and handed to `push`.'''
    import siliconcompiler

    pushed, registered = [], []

    skip_the_daemon(bootstrap, monkeypatch, registered=False)
    monkeypatch.setattr(bootstrap, "published_on", lambda image: "20260924")
    # Every tool answers a different version, which is what made the last win.
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


def test_what_it_holds_is_logged_with_both_numbers_where_they_differ(
        bootstrap, monkeypatch):
    '''`verilator` says 5.052 and PEP 440 stores 5.52: the operator is owed the
    first. Silent about a tool not there; loud about one that did not parse.'''
    said = []
    monkeypatch.setattr(bootstrap, "say", said.append)

    bootstrap.say_what_it_holds({
        "verilator": {"version": "5.52", "reported": "5.052", "present": True},
        "yosys": {"version": "0.69", "reported": "0.69", "present": True},
        "magic": {"version": None, "reported": None, "present": False},
        "gtkwave": {"version": None, "reported": "initialize",
                    "unparsed": "initialize", "present": True}})

    assert "  verilator: 5.52  (reported 5.052)" in said
    assert "  yosys: 0.69" in said
    assert not any(line.startswith("  magic:") for line in said)
    assert any("gtkwave" in line and "'initialize' is not a version" in line
               for line in said)


def test_each_image_declares_only_what_the_probe_found_in_it(bootstrap):
    '''Every tool is asked of every image, and each declares only what the probe found, since a node
    sent to an image without its tool fails. The small image still declares `slang`, which arrives
    with siliconcompiler, and cocotb where it is found.'''
    assert bootstrap.AS_DISTRIBUTION["slang"] == "pyslang"
    assert "slang" in bootstrap.TOOLS

    register(bootstrap,
             {"openroad": {"kind": "tool", "version": "26.3", "present": True},
              "slang": {"kind": "tool", "version": "11.0.0", "present": True},
              "cocotb": {"kind": "python", "version": "2.1.3", "present": True}},
             {"slang": {"kind": "tool", "version": "11.0.0", "present": True},
              "cocotb": {"kind": "python", "version": None, "present": False}})

    added = software(bootstrap)
    assert added["slang"][2:4] == ["-kind", "tool"]
    assert added["cocotb"][2:4] == ["-kind", "python"]
    assert ["add-version", "slang", "11.0.0"] in bootstrap.calls

    runtime, tools = commands(bootstrap, "add-image")
    assert "slang==11.0.0" in runtime
    assert not [arg for arg in runtime if arg.startswith(("openroad==", "cocotb=="))]
    assert {"openroad==26.3", "slang==11.0.0", "cocotb==2.1.3"} <= set(tools)
    assert not [arg for arg in tools if arg.startswith("magic==")]


def test_an_image_missing_a_tool_it_would_claim_is_refused(bootstrap):
    '''The WHOLE image: a row claiming a tool that is not there gets a node
    placed, dispatched and killed (the `bsc` failure, caught earlier).'''
    held = {tool: {"kind": "tool", "version": "1.0", "present": True}
            for tool in bootstrap.TOOLS}
    held["openroad"] = {"kind": "tool", "version": None, "present": False}

    with pytest.raises(SystemExit, match="does not hold openroad"):
        register(bootstrap, held)

    assert not commands(bootstrap, "add-image")


def test_a_tool_nobody_drives_cannot_be_tested_and_is_not_refused(bootstrap):
    '''Untestable is not absent: not refused, and declared by nothing.'''
    register(bootstrap, {tool: {"kind": "tool", "version": None, "present": None}
                         for tool in bootstrap.TOOLS})

    images = commands(bootstrap, "add-image")
    assert images
    assert not [arg for arg in images[-1] if arg.startswith("openroad==")]


def digest(letter):
    return "sha256:" + letter * 64


def pushed(bootstrap, monkeypatch, runtime, tools):
    """The classic daemon, answering for two images pushed as these digests.
    None is an image never pushed: a rebuild that changed something."""
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


def on_containerd(bootstrap, monkeypatch, runtime, tools):
    """The containerd store: the ID is an index whose digest changes every
    build (its attestation carries the build time), with the image's own
    manifest listed beside the attestation."""
    local = {bootstrap.RUNTIME_IMAGE: runtime, bootstrap.STACK_IMAGE: tools}

    def get(path):
        assert path.endswith("?manifests=1"), path
        return {
            "Id": digest("e"), "RepoDigests": [],
            "Manifests": [
                {"Kind": "image",
                 "Descriptor": {"digest": local[path.split("/")[2]]},
                 "ImageData": {"Platform": {"os": "linux", "architecture": "amd64"}}},
                {"Kind": "attestation", "Descriptor": {"digest": digest("d")}}]}

    monkeypatch.setattr(bootstrap, "_get", get)


def registered(bootstrap, monkeypatch, version, runtime, tools, staged=True):
    """A store holding both images live at `version`, as a finished bootstrap
    leaves it."""
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


@pytest.mark.parametrize("daemon,version,runtime,tools,staged,left_alone", [
    (pushed, "0.38.9", digest("a"), digest("b"), True, True),
    # Rebuilt: the image under that name was never pushed.
    (pushed, "0.38.9", digest("a"), None, True, False),
    # Pushed, but the store holds a different build at that reference.
    (pushed, "0.38.9", digest("a"), digest("c"), True, False),
    # A new SiliconCompiler version is a new reference.
    (pushed, "0.39.0", digest("a"), digest("b"), True, False),
    # Registered and never unpacked.
    (pushed, "0.38.9", digest("a"), digest("b"), False, False),
    # A cache-hit rebuild has a new ID and pushed digest; its own manifest
    # did not move, so it is still registered.
    (on_containerd, "0.38.9", digest("a"), digest("b"), True, True),
    (on_containerd, "0.38.9", digest("a"), digest("c"), True, False),
])
def test_an_image_already_registered_and_staged_is_left_alone(
        bootstrap, monkeypatch, daemon, version, runtime, tools, staged, left_alone):
    registered(bootstrap, monkeypatch, "0.38.9", digest("a"), digest("b"), staged=staged)
    daemon(bootstrap, monkeypatch, runtime=runtime, tools=tools)

    assert bootstrap.already_registered(version) is left_alone


def test_no_store_is_not_registered_and_is_not_created(bootstrap, monkeypatch):
    '''Asking must not write: the first registry command creates the store.'''
    monkeypatch.setattr(bootstrap, "DATADIR", Path("sc_server").resolve())
    pushed(bootstrap, monkeypatch, runtime=digest("a"), tools=digest("b"))

    assert not bootstrap.already_registered("0.38.9")
    assert not (bootstrap.DATADIR / "server.db").exists()


def test_main_neither_probes_nor_pushes_what_is_already_registered(
        bootstrap, monkeypatch):
    '''Every `docker compose up` used to probe, push and re-register both.'''
    def refuse(*args, **kwargs):
        raise AssertionError("bootstrap did work there was no need for")

    skip_the_daemon(bootstrap, monkeypatch, registered=True)
    for step in ("published_on", "ask_image", "push", "register"):
        monkeypatch.setattr(bootstrap, step, refuse)

    assert bootstrap.main() == 0


def posts(bootstrap, monkeypatch):
    posted = []

    def post(path, headers=None):
        posted.append(path)
        if "/push?" in path:
            return [{"status": f"0.38.9: digest: {digest('a')} size: 2008"}]
        return {}

    monkeypatch.setattr(bootstrap, "_post", post)
    return posted


def test_only_the_images_own_manifest_is_pushed(bootstrap, monkeypatch):
    '''So the digest pushed and registered is the one `already_registered`
    compares, not the index around it.'''
    on_containerd(bootstrap, monkeypatch, runtime=digest("a"), tools=digest("b"))
    posted = posts(bootstrap, monkeypatch)

    assert bootstrap.push(bootstrap.RUNTIME_IMAGE, "sc-runtime", "0.38.9") == digest("a")

    pushes = [path for path in posted if "/push?" in path]
    assert len(pushes) == 1
    platform = urllib.parse.parse_qs(urllib.parse.urlsplit(pushes[0]).query)["platform"]
    assert json.loads(platform[0]) == {"os": "linux", "architecture": "amd64"}


def test_the_classic_store_pushes_the_whole_image(bootstrap, monkeypatch):
    '''No index there, so no platform to send.'''
    pushed(bootstrap, monkeypatch, runtime=None, tools=None)
    posted = posts(bootstrap, monkeypatch)

    bootstrap.push(bootstrap.RUNTIME_IMAGE, "sc-runtime", "0.38.9")

    assert not any("platform=" in path for path in posted)


def test_the_rig_records_which_compute_node_ran_what(bootstrap, monkeypatch):
    '''The rig turns on `track_provenance`, which a real deployment keeps off,
    in a config file the server starts with.'''
    from siliconcompiler.remote.server.config import Config

    datadir = Path("datadir").resolve()
    datadir.mkdir()
    monkeypatch.setattr(bootstrap, "DATADIR", datadir)

    bootstrap.write_config()

    assert json.loads((datadir / "config.json").read_text())["track_provenance"] is True
    assert Config.load(datadir)["track_provenance"] is True
    assert Config.load(datadir / "nowhere")["track_provenance"] is False
