import pytest

import os.path

from pathlib import Path

from siliconcompiler import Project, Design

from siliconcompiler.utils.paths import cwdir, cwdirsafe, builddir, jobdir, workdir, \
    collectiondir, cachedir, datarootdir, toolcachedir


def test_cwdir():
    assert cwdir(Project()) == os.path.abspath(".")


def test_cwdir_not_project():
    with pytest.raises(TypeError, match=r"^project must be a Project type$"):
        cwdir(Design())


def test_cwdirsafe():
    assert cwdirsafe(Project()) == os.path.abspath(".")


def test_cwdirsafe_not_project():
    assert cwdirsafe(Design()) == os.path.abspath(".")


def test_builddir():
    assert builddir(Project()) == os.path.abspath("build")


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_builddir_notproject(arg):
    with pytest.raises(TypeError, match=r"^project must be a Project type$"):
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
    with pytest.raises(ValueError, match=r"^name has not been set$"):
        jobdir(Project())


def test_jobdir():
    assert jobdir(Project("testname")) == \
        os.path.abspath(os.path.join("build", "testname", "job0"))


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_jobdir_notproject(arg):
    with pytest.raises(TypeError, match=r"^project must be a Project type$"):
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


def test_cachedir_default():
    assert cachedir(Project()) == os.path.join(Path.home(), ".sc", "cache")


def test_cachedir_no_project():
    """A data source can resolve without a project, and still needs a cache."""
    assert cachedir(None) == os.path.join(Path.home(), ".sc", "cache")


def test_cachedir_not_project():
    """Unlike the rest of this module, any schema will do."""
    assert cachedir(Design()) == os.path.join(Path.home(), ".sc", "cache")


def test_cachedir_from_option():
    project = Project("testname")
    project.option.set_cachedir(os.path.abspath("thiscache"))
    # Compared as paths, not as strings: a configured directory comes back from
    # find_files posix-style, which on Windows is not what abspath() spells.
    assert Path(cachedir(project)) == Path(os.path.abspath("thiscache"))


def test_cachedir_from_option_relative():
    project = Project("testname")
    project.option.set_cachedir("thiscache")
    assert Path(cachedir(project)) == Path(os.path.abspath("thiscache"))


def test_datarootdir():
    project = Project("testname")
    project.option.set_cachedir("thiscache")
    assert Path(datarootdir(project)) == Path(os.path.abspath("thiscache")) / "dataroot"


def test_datarootdir_default():
    assert datarootdir(None) == os.path.join(Path.home(), ".sc", "cache", "dataroot")


def test_toolcachedir():
    project = Project("testname")
    project.option.set_cachedir("thiscache")
    assert Path(toolcachedir(project)) == Path(os.path.abspath("thiscache")) / "tools"


def test_toolcachedir_default():
    assert toolcachedir(None) == os.path.join(Path.home(), ".sc", "cache", "tools")


def test_cache_areas_are_distinct():
    """The two areas must not overlap, or a sweep of one would reach the other."""
    project = Project("testname")
    project.option.set_cachedir("thiscache")

    assert datarootdir(project) != toolcachedir(project)
    assert os.path.dirname(datarootdir(project)) == cachedir(project)
    assert os.path.dirname(toolcachedir(project)) == cachedir(project)
