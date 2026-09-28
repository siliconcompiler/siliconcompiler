import logging
import pytest

import os.path

from pathlib import Path
from unittest.mock import patch

from siliconcompiler import Project, Design, Flowgraph, Task
from siliconcompiler.utils.curation import collect, archive, filter_collection_keys
from siliconcompiler.utils.paths import collectiondir
from siliconcompiler.schema.parametervalue import PathNodeValue


class FauxTask0(Task):
    def tool(self):
        return "tool0"

    def task(self):
        return "task0"


class FauxTask1(Task):
    def tool(self):
        return "tool1"

    def task(self):
        return "task1"


@pytest.fixture
def path_keys():
    def _run(project):
        keys = []
        for key in project.allkeys():
            param = project.get(*key, field=None)
            if param.is_path:
                keys.extend((key, step, index)
                            for _, step, index in param.getvalues(return_values=False))
        return filter_collection_keys(keys)
    return _run


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_collect_notproject(arg):
    with pytest.raises(TypeError, match=r"^project must be a Project$"):
        collect(arg, keys=[])


def test_collect_file_verbose(project_logger, caplog, path_keys):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("top.v")
    with open("top.v", "w") as f:
        f.write("test")

    proj = Project(design)
    project_logger(proj)
    proj.logger.setLevel(logging.INFO)

    collect(proj, keys=path_keys(proj))

    assert f"Collecting files to: {collectiondir(proj)}" in caplog.text
    assert f"  Collecting file: {os.path.abspath('top.v')}" in caplog.text


def test_collect_file_not_verbose(project_logger, caplog, path_keys):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("top.v")
    with open("top.v", "w") as f:
        f.write("test")

    proj = Project(design)
    project_logger(proj)
    proj.logger.setLevel(logging.INFO)

    collect(proj, keys=path_keys(proj), verbose=False)

    assert caplog.text == ""


def test_collect_file_update(path_keys):
    # Checks if collected files are properly updated after editing

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("fake.v")

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('fake')

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    filename = design.get_file(fileset="rtl", filetype="verilog")[0]

    assert len(os.listdir(collectiondir(proj))) == 1
    with open(os.path.join(collectiondir(proj), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'fake'

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('newfake')

    # Rerun collect
    with patch("shutil.rmtree") as rmtree:
        collect(proj, keys=path_keys(proj))
        rmtree.assert_called_once_with(os.path.join(os.path.dirname(collectiondir(proj)),
                                                    "sc_previous_collection"))

    assert len(os.listdir(collectiondir(proj))) == 1
    with open(os.path.join(collectiondir(proj), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'newfake'


def test_collect_file_incremental(path_keys):
    # Checks if collected files are properly updated after editing

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("fake.v")

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('fake')

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    filename = design.get_file(fileset="rtl", filetype="verilog")[0]

    assert len(os.listdir(collectiondir(proj))) == 1
    with open(os.path.join(collectiondir(proj), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'fake'

    # Remove file, should still be findable in previous collection
    os.remove('fake.v')

    # Rerun collect
    collect(proj, keys=path_keys(proj))
    assert len(os.listdir(collectiondir(proj))) == 1
    with open(os.path.join(collectiondir(proj), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'fake'


def test_collect_directory(path_keys):
    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("testingdir")
            design.add_file("testingdir/test.v")

    os.makedirs('testingdir', exist_ok=True)

    with open('testingdir/test.v', 'w') as f:
        f.write('test')

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    assert len(os.listdir(collectiondir(proj))) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(collectiondir(proj))
    assert os.listdir(path) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(collectiondir(proj))


def test_collect_subdirectory(path_keys):
    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("testingdir")
            design.add_file("testingdir/subdir/test.v")

    os.makedirs('testingdir/subdir', exist_ok=True)

    with open('testingdir/subdir/test.v', 'w') as f:
        f.write('test')

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    assert len(os.listdir(collectiondir(proj))) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(collectiondir(proj))
    assert os.listdir(path) == ['subdir']
    assert os.listdir(os.path.join(path, "subdir")) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(collectiondir(proj))


def test_collect_script_inside_refdir_not_duplicated(path_keys):
    """A script that lives inside a refdir should be collected only via the refdir,
    not also as a separate hashed file. Regression test for sc-issue duplicating
    OpenROAD scripts that are already part of the collected refdir.

    Mimics the sc-issue path: collect() is called with an explicit ``directory``
    that differs from ``collectiondir(project)``, so the script's refdir search
    path (which uses ``collectiondir(project)`` internally) resolves to the
    original filesystem location rather than the destination collection dir."""

    os.makedirs('scripts/apr', exist_ok=True)
    with open('scripts/apr/sc_test.tcl', 'w') as f:
        f.write('# entry script')
    with open('scripts/helper.tcl', 'w') as f:
        f.write('# helper')

    design = Design("testdesign")
    design.set_topmodule("top", fileset="rtl")
    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("step", FauxTask0())
    proj.set_flow(flow)

    task = FauxTask0.find_task(proj)
    task.set_refdir("scripts")
    task.set_script("apr/sc_test.tcl")

    proj.set("tool", "tool0", "task", "task0", "refdir", True, field="copy")
    proj.set("tool", "tool0", "task", "task0", "script", True, field="copy")

    # Collect into a directory that is NOT the project's normal collectiondir,
    # to match how sc-issue redirects collection into a temporary issue dir.
    custom_collect_dir = os.path.abspath("issue_collect")
    collect(proj, keys=path_keys(proj), directory=custom_collect_dir)

    collected = os.listdir(custom_collect_dir)
    # Only the refdir should land in the collection — the script lives inside it.
    assert len(collected) == 1, \
        f"Expected only refdir to be collected, got: {collected}"

    refdir_collected = os.path.join(custom_collect_dir, collected[0])
    assert os.path.isdir(refdir_collected)
    assert os.path.isfile(os.path.join(refdir_collected, "apr", "sc_test.tcl"))

    # The script's standalone hashed name must NOT have been copied separately.
    script_hashed = PathNodeValue.generate_hashed_path("apr/sc_test.tcl", None)
    assert not os.path.exists(os.path.join(custom_collect_dir, script_hashed)), \
        "Script was copied separately even though it lives inside the collected refdir"


def test_collect_overlapping_refdirs_dedup_across_keys(path_keys):
    """If two refdir entries point to a parent and child directory, only the parent
    should be copied. Verifies the dedup set is shared across keys."""

    os.makedirs('parent/child', exist_ok=True)
    with open('parent/top.txt', 'w') as f:
        f.write('top')
    with open('parent/child/inner.txt', 'w') as f:
        f.write('inner')

    design = Design("testdesign")
    design.set_topmodule("top", fileset="rtl")
    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("step", FauxTask0())
    proj.set_flow(flow)

    task = FauxTask0.find_task(proj)
    task.set_refdir("parent")
    task.add("refdir", "parent/child")

    proj.set("tool", "tool0", "task", "task0", "refdir", True, field="copy")

    collect(proj, keys=path_keys(proj))

    # Only the parent dir should be present in the collection
    collected = os.listdir(collectiondir(proj))
    assert len(collected) == 1, \
        f"Expected only parent refdir, got: {collected}"

    child_hashed = PathNodeValue.generate_hashed_path("parent/child", None)
    assert not os.path.exists(os.path.join(collectiondir(proj), child_hashed)), \
        "Child refdir was copied separately even though parent already covers it"


def test_collect_file_with_false():
    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=False):
            design.add_file("fake.v")

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('fake')

    proj = Project(design)
    collect(proj, keys=[])

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 0


def test_collect_file_home(monkeypatch, path_keys):
    def _mock_home():
        return Path(os.getcwd()) / "home"

    monkeypatch.setattr(Path, 'home', _mock_home)

    _mock_home().mkdir(exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir(str(Path.home()))

    with open(Path.home() / "test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_build(path_keys):
    os.makedirs('build', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("build")

    with open("build/test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_hidden_dir(path_keys):
    os.makedirs('test/.test', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open("test/.test/test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_hidden_file(path_keys):
    os.makedirs('test', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open("test/.test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_whitelist_error(path_keys):
    os.makedirs('test/testing', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open('test/test', 'w') as f:
        f.write('test')

    proj = Project(design)

    with pytest.raises(RuntimeError,
                       match=r"^.* is not on the approved collection list\.$"):
        collect(proj, keys=path_keys(proj), whitelist=[os.path.abspath('not_test_folder')])

    assert len(os.listdir(collectiondir(proj))) == 0


def test_collect_file_whitelist_pass(path_keys):
    os.makedirs('test/testing', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open('test/test', 'w') as f:
        f.write('test')

    proj = Project(design)
    collect(proj, keys=path_keys(proj), whitelist=[os.path.abspath('test')])

    assert len(os.listdir(collectiondir(proj))) == 1


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_archive_notproject(arg):
    with pytest.raises(TypeError, match=r"^project must be a Project$"):
        archive(arg)


def test_archive_no_jobs():
    with pytest.raises(ValueError, match=r"^no history to archive$"):
        archive(Project())


def test_archive_select_job():
    proj = Project(Design("testdesign"))
    proj.set("option", "jobname", "thisjob")
    proj._record_history()
    proj.set("option", "jobname", "thatjob")
    proj._record_history()

    with patch("siliconcompiler.Project.history") as history:
        history.return_value = proj
        archive(proj)

        history.assert_called_once_with("thatjob")


def test_archive_default_archive(project_logger, caplog):
    proj = Project(Design("testdesign"))
    project_logger(proj)
    proj.logger.setLevel(logging.INFO)
    proj._record_history()

    archive(proj)

    assert "Creating archive testdesign_job0.tgz..." in caplog.text
    assert os.path.isfile("testdesign_job0.tgz")


def test_archive_archive_name(project_logger, caplog):
    proj = Project(Design("testdesign"))
    project_logger(proj)
    proj.logger.setLevel(logging.INFO)
    proj._record_history()

    archive(proj, archive_name="test.tar.gz")

    assert "Creating archive test.tar.gz..." in caplog.text
    assert os.path.isfile("test.tar.gz")


def test_archive(project_logger, caplog):
    design = Design("testdesign")
    design.set_topmodule("top", fileset="test")
    proj = Project(design)
    proj.add_fileset("test")
    project_logger(proj)
    proj.logger.setLevel(logging.INFO)

    flow = Flowgraph("testflow")
    flow.node("stepone", FauxTask0())
    flow.node("steptwo", FauxTask0())
    flow.edge("stepone", "steptwo")
    proj.set_flow(flow)

    proj._record_history()

    with patch("siliconcompiler.scheduler.SchedulerNode.archive") as node_archive:
        archive(proj)
        assert node_archive.call_count == 2

    assert "Creating archive testdesign_job0.tgz..." in caplog.text
    assert os.path.isfile("testdesign_job0.tgz")
