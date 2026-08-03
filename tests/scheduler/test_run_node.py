import pytest

from unittest.mock import patch

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.scheduler import run_node
from siliconcompiler.tools.builtin.nop import NOPTask


@pytest.fixture
def manifest():
    """Writes a minimal manifest and returns its path."""
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())

    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    project = Project(design)
    project.add_fileset("rtl")
    project.set_flow(flow)

    path = "manifest.pkg.json"
    project.write_manifest(path)
    return path


def run_main(manifest, cachemap=None):
    """Runs main() without executing the node."""
    argv = ["run_node", "-cfg", manifest, "-cwd", ".", "-builddir", "build",
            "-step", "stepone", "-index", "0"]
    if cachemap:
        argv.append("-cachemap")
        argv.extend(cachemap)

    with patch("sys.argv", argv), \
         patch("siliconcompiler.scheduler.run_node.SchedulerNode"):
        assert run_node.main() == 0


def test_no_cachemap(manifest):
    run_main(manifest)

    assert MPManager.get_path_cache().export()["paths"] == {}


def test_cachemap_seeds_paths(manifest):
    run_main(manifest, ["abc123:/some/path", "def456:/other/path"])

    assert MPManager.get_path_cache().get("abc123") == "/some/path"
    assert MPManager.get_path_cache().get("def456") == "/other/path"


def test_cachemap_path_with_colon(manifest):
    """A cache ID is a hex digest, so everything after the first colon is path."""
    run_main(manifest, [r"abc123:C:\data\thing"])

    assert MPManager.get_path_cache().get("abc123") == r"C:\data\thing"


def test_cachemap_path_with_many_colons(manifest):
    run_main(manifest, ["abc123:/a:b:c/d"])

    assert MPManager.get_path_cache().get("abc123") == "/a:b:c/d"


@pytest.mark.parametrize("entry", ("noseparator", ":", ":/only/path", "abc123:", ""))
def test_cachemap_malformed_entries_are_skipped(manifest, entry):
    """A malformed entry must be ignored, not crash the node before it starts."""
    run_main(manifest, [entry])

    assert MPManager.get_path_cache().export()["paths"] == {}


def test_cachemap_keeps_good_entries_alongside_bad(manifest):
    run_main(manifest, ["noseparator", "abc123:/some/path", "abc123:"])

    assert MPManager.get_path_cache().export()["paths"] == {"abc123": "/some/path"}
