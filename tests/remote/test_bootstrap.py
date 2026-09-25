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
            wanted = task_cls().image_requirement()
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
