import logging
import pytest

import os.path

from pathlib import Path

from siliconcompiler import Project, Design
from siliconcompiler.utils.collect import getcollectiondir, collect


def test_getcollectiondir():
    assert getcollectiondir(Project("testname")) == \
        os.path.abspath(os.path.join("build", "testname", "job0", "sc_collected_files"))


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_getcollectiondir_notproject(arg):
    assert getcollectiondir(arg) is None


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

    assert f"Collecting files to: {getcollectiondir(proj)}" in caplog.text
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

    assert len(os.listdir(getcollectiondir(proj))) == 1
    with open(os.path.join(getcollectiondir(proj), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'fake'

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('newfake')

    # Rerun collect
    collect(proj, )
    assert len(os.listdir(getcollectiondir(proj))) == 1
    with open(os.path.join(getcollectiondir(proj), os.path.basename(filename)), 'r') as f:
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

    assert len(os.listdir(getcollectiondir(proj))) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(getcollectiondir(proj))
    assert os.listdir(path) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(getcollectiondir(proj))


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

    assert len(os.listdir(getcollectiondir(proj))) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(getcollectiondir(proj))
    assert os.listdir(path) == ['subdir']
    assert os.listdir(os.path.join(path, "subdir")) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(getcollectiondir(proj))


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
    assert len(os.listdir(getcollectiondir(proj))) == 0


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
    assert len(os.listdir(getcollectiondir(proj))) == 1
    subdir = os.path.join(getcollectiondir(proj), os.listdir(getcollectiondir(proj))[0])
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
    assert len(os.listdir(getcollectiondir(proj))) == 1
    subdir = os.path.join(getcollectiondir(proj), os.listdir(getcollectiondir(proj))[0])
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
    assert len(os.listdir(getcollectiondir(proj))) == 1
    subdir = os.path.join(getcollectiondir(proj), os.listdir(getcollectiondir(proj))[0])
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
    assert len(os.listdir(getcollectiondir(proj))) == 1
    subdir = os.path.join(getcollectiondir(proj), os.listdir(getcollectiondir(proj))[0])
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

    assert len(os.listdir(getcollectiondir(proj))) == 0


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

    assert len(os.listdir(getcollectiondir(proj))) == 1
