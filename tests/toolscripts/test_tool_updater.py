import importlib.util
import os
import re
import sys

import pytest

import siliconcompiler


TOOLSCRIPTS = os.path.join(os.path.dirname(siliconcompiler.__file__), "toolscripts")


def _load_tools():
    # toolscripts is data, not a package: the install scripts run _tools.py as a
    # script and there is no __init__.py to import through.
    spec = importlib.util.spec_from_file_location(
        "sc_toolscripts_tools", os.path.join(TOOLSCRIPTS, "_tools.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sc_tools = _load_tools()


def _tag_pinned_tools():
    """The auto-updated tools whose pin is a tag rather than a commit sha.

    These are the ones that go through bump_commit_tag, so these are the ones
    whose tag selection has to be able to see their own pin.
    """

    for tool in sc_tools.get_tools():
        if not sc_tools.get_field(tool, "auto-update"):
            continue
        if not sc_tools.get_field(tool, "git-url"):
            continue
        pin = sc_tools.get_field(tool, "git-commit")
        if not pin or re.fullmatch(r"[a-f0-9]{40}", pin):
            continue
        yield tool, pin


@pytest.mark.parametrize("name", [
    # Every shape of release tag the tracked repositories actually use.
    "v13_0",            # icarus
    "v8-s20060822",     # icarus, and old enough to lose on date
    "v1.87",            # surelog
    "v5.038",           # verilator
    "v6.0.0",           # ghdl
    "2026.01",          # bluespec
    "2025.01.1",        # bluespec
    "v0.68",            # yosys, sby
    "yosys-0.44",       # yosys, before it moved to a v prefix
    "0.45",             # yosys, before that
    "Release-7.10.0",   # xyce
    "v3.3.116",         # gtkwave
    "v0.7.0",           # surfer
    "0.9.1",            # bitwuzla
    "3.2.4",            # boolector
    "llvmorg-19.1.5",   # mlir
    "nextpnr-0.9",      # nextpnr
    "v1.1",             # icepack
])
def test_is_version_tag_accepts_releases(name):
    assert sc_tools.is_version_tag(name, "")


@pytest.mark.parametrize("name", [
    # Real pre-release tags from the same repositories. A project opens a
    # release series before it finishes it, so for as long as the series is open
    # the newest tag by date is a candidate the updater must not take.
    "v6.0.0-rc.1",          # ghdl
    "v6.0.0-rc2",           # ghdl, same series, different spelling
    "v5.0.0-rc6",           # ghdl
    "v0.36-rc1",            # ghdl
    "v1.0.0rc1",            # ghdl, no separator at all
    "v0.35rc2",             # ghdl
    "v2.0.0-M2",            # sbt
    "v2.0.0-RC16",          # sbt
    "v2.0.0-RC13-1",        # sbt, a respin of an rc
    "0.13.5-RC5",           # sbt
    "2023.00.90alpha",      # bluespec
    "v0_1rc1",              # icarus
    "pymod/v0.26.0.dev15",  # klayout
    "ghdl_0.31dev",         # ghdl, the marker run onto a digit with no number
    "v0.12.0-Beta",         # sbt, a marker after a separator with no number
])
def test_is_version_tag_rejects_prereleases(name):
    assert not sc_tools.is_version_tag(name, "")


@pytest.mark.parametrize("name", [
    # A marker only counts where it is a marker. Each of these carries one as
    # the head of an ordinary word, and each is a release.
    "v1.0-master",
    "v1.0-mingw",
    "v1.0.0-macos",
    "v1.0-development",
    "smtcomp-2018",     # boolector, and its real tag
    "llvmorg-19.1.5",   # mlir: the m of llvm is not a milestone
])
def test_is_version_tag_keeps_markers_inside_words(name):
    assert sc_tools.is_version_tag(name, "")


@pytest.mark.parametrize("marker", [
    "rc", "alpha", "beta", "pre", "preview", "snapshot", "dev", "milestone", "m",
])
def test_is_version_tag_rejects_every_marker_in_both_forms(marker):
    """Every marker has to be recognised in both spellings.

    The two halves of the pattern were written separately and kept disagreeing.
    First on the marker list: the digit form knew only rc, alpha and beta, so
    v1.0-dev1 was rejected while v1.0dev1 was accepted as a release. Then on
    the number: the separator form required one, so v1.0rc was rejected while
    v1.0-rc was not, and sbt's real v0.12.0-Beta went through as a release.
    """

    assert not sc_tools.is_version_tag(f"v1.0-{marker}1", "")   # separator
    assert not sc_tools.is_version_tag(f"v1.0.{marker}1", "")   # separator
    assert not sc_tools.is_version_tag(f"v1.0{marker}1", "")    # onto a digit
    assert not sc_tools.is_version_tag(f"v1.0{marker}", "")     # unnumbered
    assert not sc_tools.is_version_tag(f"v1.0-{marker}", "")    # and both at once

    # The marker is a marker only at a boundary. Nothing here is a pre-release.
    assert sc_tools.is_version_tag(f"v1.0-x{marker}1", "")


@pytest.mark.parametrize("name", [
    # Tags that name a branch or a build rather than a release. These matter
    # because a moving tag always has the newest commit date and would win every
    # comparison: bitwuzla's "latest" was repointed the day this test was
    # written, well after its 0.9.1 release.
    "latest",           # bitwuzla
    "nightly",          # gtkwave
    "resources",        # yosys
    "docs-previewtest",  # yosys
    "test",             # surfer
])
def test_is_version_tag_rejects_non_versions(name):
    assert not sc_tools.is_version_tag(name, "")


def test_is_version_tag_honours_prefix():
    assert sc_tools.is_version_tag("Release-7.10.0", "Release-")
    assert not sc_tools.is_version_tag("Release-7.10.0", "v")
    assert not sc_tools.is_version_tag("2026.01", "v")


@pytest.mark.parametrize("tool,pin", list(_tag_pinned_tools()))
def test_pinned_tag_is_selectable(tool, pin):
    """A tool marked auto-update must be able to select the tag it is pinned to.

    Without this the flag can be quietly inert. bluespec's tags are 2026.01 and
    the like, so under the default 'v' prefix its updater matched no tag at all,
    found no newest, and returned no change on every run for as long as the flag
    had been set.
    """

    prefix = sc_tools.get_field(tool, "version-prefix")
    if prefix is None:
        prefix = "v"

    assert sc_tools.is_version_tag(pin, prefix), \
        f"{tool} is pinned to {pin!r}, which its own tag selection would skip"


def test_bump_commit_routes_tags_to_tag_selection(monkeypatch):
    """A pin that is not a 40-character sha has to take the tag path.

    icarus is pinned to the tag v13_0, having previously been pinned to a commit
    sha, and the two are told apart by nothing but that regex.
    """

    class FakeCommit:
        hexsha = "0" * 40

    class FakeRepo:
        head = type("head", (), {"commit": FakeCommit})

        @staticmethod
        def clone_from(url, work_dir, *args, **kwargs):
            return FakeRepo()

    monkeypatch.setitem(sys.modules, "git", type("git", (), {"Repo": FakeRepo}))

    tagged = []
    monkeypatch.setattr(sc_tools, "bump_commit_tag",
                        lambda tools, tool: (tagged.append(tool), ("stub", None))[1])

    tools = {
        "tagged": {"git-url": "https://example.invalid/x.git", "git-commit": "v13_0"},
        "sha": {"git-url": "https://example.invalid/x.git",
                "git-commit": "84e3ff1eb2c36302cef42e4f70a69efe4cfbb126"},
    }

    assert sc_tools.bump_commit(tools, "tagged") == ("stub", None)
    assert tagged == ["tagged"]

    # A sha pin clones and reads HEAD instead, and must not reach the tag path.
    assert sc_tools.bump_commit(tools, "sha")[0] == "0" * 40
    assert tagged == ["tagged"]
