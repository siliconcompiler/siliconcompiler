import logging
import pytest

import os.path

from pathlib import Path
from unittest.mock import patch

from siliconcompiler.project import Project
from siliconcompiler import Design, Flowgraph, Task
from siliconcompiler.utils.curation import collect, archive
from siliconcompiler.utils.paths import collectiondir


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


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_collect_notproject(arg):
    with pytest.raises(TypeError, match="project must be a Project"):
        collect(arg)


def test_collect_file_verbose(monkeypatch, caplog):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("top.v")
    with open("top.v", "w") as f:
        f.write("test")

    proj = Project(design)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    collect(proj)

    assert f"Collecting files to: {collectiondir(proj)}" in caplog.text
    assert f"  Collecting file: {os.path.abspath('top.v')}" in caplog.text


def test_collect_file_not_verbose(monkeypatch, caplog):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("top.v")
    with open("top.v", "w") as f:
        f.write("test")

    proj = Project(design)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    collect(proj, verbose=False)

    assert caplog.text == ""


def test_collect_file_update():
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
    collect(proj, )

    filename = design.get_file(fileset="rtl", filetype="verilog")[0]

    assert len(os.listdir(collectiondir(proj))) == 1
    with open(os.path.join(collectiondir(proj), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'fake'

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('newfake')

    # Rerun collect
    collect(proj, )
    assert len(os.listdir(collectiondir(proj))) == 1
    with open(os.path.join(collectiondir(proj), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'newfake'


def test_collect_directory():
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
    collect(proj, )

    assert len(os.listdir(collectiondir(proj))) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(collectiondir(proj))
    assert os.listdir(path) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(collectiondir(proj))


def test_collect_subdirectory():
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
    collect(proj)

    assert len(os.listdir(collectiondir(proj))) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(collectiondir(proj))
    assert os.listdir(path) == ['subdir']
    assert os.listdir(os.path.join(path, "subdir")) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(collectiondir(proj))


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
    collect(proj, )

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 0


def test_collect_file_home(monkeypatch):
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
    collect(proj, )

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_build():
    os.makedirs('build', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("build")

    with open("build/test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    collect(proj, )

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_hidden_dir():
    os.makedirs('test/.test', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open("test/.test/test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    collect(proj, )

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_hidden_file():
    os.makedirs('test', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open("test/.test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    collect(proj, )

    # No files should have been collected
    assert len(os.listdir(collectiondir(proj))) == 1
    subdir = os.path.join(collectiondir(proj), os.listdir(collectiondir(proj))[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_whitelist_error():
    os.makedirs('test/testing', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open('test/test', 'w') as f:
        f.write('test')

    proj = Project(design)

    with pytest.raises(RuntimeError, match=".* is not on the approved collection list"):
        collect(proj, whitelist=[os.path.abspath('not_test_folder')])

    assert len(os.listdir(collectiondir(proj))) == 0


def test_collect_file_whitelist_pass():
    os.makedirs('test/testing', exist_ok=True)

    # Create instance of design
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open('test/test', 'w') as f:
        f.write('test')

    proj = Project(design)
    collect(proj, whitelist=[os.path.abspath('test')])

    assert len(os.listdir(collectiondir(proj))) == 1


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_archive_notproject(arg):
    with pytest.raises(TypeError, match="project must be a Project"):
        archive(arg)


def test_archive_no_jobs():
    with pytest.raises(ValueError, match="no history to archive"):
        archive(Project())


def test_archive_select_job():
    proj = Project(Design("testdesign"))
    proj.set("option", "jobname", "thisjob")
    proj._record_history()
    proj.set("option", "jobname", "thatjob")
    proj._record_history()

    with patch("siliconcompiler.project.Project.history") as history:
        history.return_value = proj
        archive(proj)

        history.assert_called_once_with("thatjob")


def test_archive_default_archive(monkeypatch, caplog):
    proj = Project(Design("testdesign"))
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    proj._record_history()

    archive(proj)

    assert "Creating archive testdesign_job0.tgz..." in caplog.text
    assert os.path.isfile("testdesign_job0.tgz")


def test_archive_archive_name(monkeypatch, caplog):
    proj = Project(Design("testdesign"))
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    proj._record_history()

    archive(proj, archive_name="test.tar.gz")

    assert "Creating archive test.tar.gz..." in caplog.text
    assert os.path.isfile("test.tar.gz")


def test_archive(monkeypatch, caplog):
    design = Design("testdesign")
    design.set_topmodule("top", fileset="test")
    proj = Project(design)
    proj.add_fileset("test")
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
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
