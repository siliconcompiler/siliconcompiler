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
    held = {tool: {"kind": "tool", "version": f"{n}.0"}
            for n, tool in enumerate(bootstrap.TOOLS)}
    drivers = {tool: f"siliconcompiler.tools.{tool}" for tool in bootstrap.TOOLS}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                       held, {}, drivers)

    refs = [call[1] for call in commands(bootstrap, "add-image")]
    assert refs == [f"{bootstrap.PULL_FROM}/sc-runtime:0.38.9",
                    f"{bootstrap.PULL_FROM}/sc-tools:0.38.9"]

    for call in commands(bootstrap, "add-image"):
        assert "siliconcompiler==0.38.9" in call


def test_a_tool_that_reported_is_registered_as_reported(bootstrap):
    held = {"yosys": {"kind": "tool", "version": "0.69"}}
    drivers = {"yosys": "siliconcompiler.tools.yosys"}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                       held, {}, drivers)

    added = [call for call in commands(bootstrap, "add-version")
             if call[1] == "yosys"]
    assert added == [["add-version", "yosys", "0.69"]]


def test_a_tool_that_said_nothing_gets_the_publish_date_and_the_mark(bootstrap):
    """🔴 `20260924` beats `2.0.1` under every comparison there is, so an
    unmarked date would outrank every real release for ever."""
    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", {}, {},
                       {tool: None for tool in bootstrap.TOOLS})

    for tool in bootstrap.TOOLS:
        assert ["add-version", tool, "20260924", "-unversioned"] in bootstrap.calls


def test_a_tool_with_a_driver_records_it_and_one_without_does_not(bootstrap):
    drivers = {tool: None for tool in bootstrap.TOOLS}
    drivers["yosys"] = "siliconcompiler.tools.yosys"

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", {}, {},
                       drivers)

    added = {call[1]: call for call in commands(bootstrap, "add-software")}
    assert added["yosys"][-2:] == ["-driver", "siliconcompiler.tools.yosys"]
    assert "-driver" not in added["openroad"]
    # And every tool says so, because the kind is stated and never derived.
    assert added["openroad"][2:4] == ["-kind", "tool"]
    assert added["siliconcompiler"][2:4] == ["-kind", "python"]


def test_the_image_declares_what_the_probe_found(bootstrap):
    """What goes in `-contains` is the version that was registered, or the
    registry refuses a version it just accepted."""
    held = {"yosys": {"kind": "tool", "version": "0.69"}}

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", held, {},
                       {"yosys": "siliconcompiler.tools.yosys"})

    tools = commands(bootstrap, "add-image")[-1]
    assert "yosys==0.69" in tools
    # Every other tool reported nothing and falls back to the date.
    assert "openroad==20260924" in tools


def test_a_driver_is_recorded_as_the_package_and_not_one_task_file(bootstrap):
    """🔴 `icarus` has no task in its package's `__init__`, so *shallowest
    module* picked whichever task file sorted first -- the probe imported that
    one module, walked no submodules because a module has none, and never saw
    the class that sets the executable. Nine tools reported and one did not."""
    found = bootstrap.drivers_for(["icarus", "klayout", "openroad"])

    assert found["icarus"] == "siliconcompiler.tools.icarus"
    assert found["klayout"] == "siliconcompiler.tools.klayout"
    assert found["openroad"] == "siliconcompiler.tools.openroad"


def test_a_name_nothing_drives_records_no_driver(bootstrap):
    assert bootstrap.drivers_for(["not-a-tool-anybody-has"]) == \
        {"not-a-tool-anybody-has": None}


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
    monkeypatch.setattr(bootstrap, "drivers_for",
                        lambda names: {name: None for name in names})
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
        "verilator": {"version": "5.52", "reported": "5.052"},
        "yosys": {"version": "0.69", "reported": "0.69"}})

    assert "  verilator: 5.52  (reported 5.052)" in said
    assert "  yosys: 0.69" in said
    assert "  openroad: no version reported" in said


def test_a_tool_whose_version_is_a_distribution_is_still_a_tool(bootstrap):
    """🔴 `slang` is a tool to a flow -- a node names it and has to be placed
    in an image holding it -- and its version is a python package, because its
    driver runs pyslang in SiliconCompiler's own process. The difference is how
    the version is read, not what it is."""
    assert bootstrap.AS_DISTRIBUTION["slang"] == "pyslang"
    assert "slang" in bootstrap.TOOLS

    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                       {"slang": {"kind": "tool", "version": "11.0.0"}}, {},
                       {tool: None for tool in bootstrap.TOOLS})

    added = {call[1]: call for call in commands(bootstrap, "add-software")}
    assert added["slang"][2:4] == ["-kind", "tool"]
    assert ["add-version", "slang", "11.0.0"] in bootstrap.calls


def test_the_runtime_image_declares_only_what_it_answered_for(bootstrap):
    """⚠️ The fallback to the publish date belongs to the TOOLS image alone.
    That one is built to contain the whole list, so a tool that said nothing is
    present and mute. The runtime image is built to contain none of them, and
    declaring a tool it does not hold sends nodes to an image that cannot run
    them."""
    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924",
                       {}, {"slang": {"kind": "tool", "version": "11.0.0"}},
                       {tool: None for tool in bootstrap.TOOLS})

    runtime, tools = commands(bootstrap, "add-image")

    assert "slang==11.0.0" in runtime
    assert "openroad==20260924" not in runtime
    # And the tools image falls back for everything that said nothing.
    assert "openroad==20260924" in tools


def test_built_at_is_a_timestamp_and_not_the_publish_date(bootstrap):
    """🔴 They are not the same thing. The date is a VERSION for a tool that
    reports none, so it has to compare as a version; `built_at` breaks the tie
    between two images carrying identical versions -- and two images built on
    the same day is the ordinary case, so a date cannot break it."""
    bootstrap.register("0.38.9", "sha256:b", "sha256:a", "20260924", {}, {},
                       {tool: None for tool in bootstrap.TOOLS})

    for call in commands(bootstrap, "add-image"):
        built = call[call.index("-built") + 1]
        assert built.startswith("2026-09-24T")
        assert built != "20260924"
