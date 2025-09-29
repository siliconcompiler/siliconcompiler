import pytest

import os.path

from pathlib import Path

from siliconcompiler.project import Project
from siliconcompiler import Design

from siliconcompiler.utils.paths import builddir, jobdir, workdir, collectiondir


def test_builddir():
    assert builddir(Project()) == os.path.abspath("build")


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_builddir_notproject(arg):
    with pytest.raises(TypeError, match="project must be a Project type"):
        builddir(arg)


def test_builddir_abspath():
    project = Project()
    project.set("option", "builddir", os.path.abspath("diffdir/buildhere"))

    assert builddir(project) == \
        Path(os.path.abspath("diffdir/buildhere")).as_posix()


def test_builddir_diff_build():
    project = Project()
    project.set("option", "builddir", "testbuild")
    assert builddir(project) == os.path.abspath("testbuild")


def test_jobdir_no_name():
    with pytest.raises(ValueError, match="name has not been set"):
        jobdir(Project())


def test_jobdir():
    assert jobdir(Project("testname")) == \
        os.path.abspath(os.path.join("build", "testname", "job0"))


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_jobdir_notproject(arg):
    with pytest.raises(TypeError, match="project must be a Project type"):
        jobdir(arg)


def test_jobdir_diff_jobname():
    prj = Project("testname")
    prj.set("option", "jobname", "thisjob")
    assert jobdir(prj) == os.path.abspath(os.path.join("build", "testname", "thisjob"))


def test_workdir_step():
    assert workdir(Project("testname"), step="thisstep") == \
        os.path.abspath(os.path.join("build", "testname", "job0", "thisstep", "0"))


def test_workdir_step_index():
    assert workdir(Project("testname"), step="thisstep", index="thisindex") == \
        os.path.abspath(os.path.join("build", "testname", "job0", "thisstep", "thisindex"))


def test_workdir_relpath():
    assert workdir(Project("testname"), step="thisstep", index="thisindex", relpath=True) == \
        os.path.join("build", "testname", "job0", "thisstep", "thisindex")


def test_collectiondir():
    assert collectiondir(Project("testname")) == \
        os.path.abspath(os.path.join("build", "testname", "job0", "sc_collected_files"))


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_collectiondir_notproject(arg):
    assert collectiondir(arg) is None
