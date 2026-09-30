import logging
import pytest
import shutil
import sys

import os.path

from pathlib import Path
from unittest.mock import Mock, patch

from siliconcompiler import Project, Design, Flowgraph, Task
from siliconcompiler.utils.curation import (
    collect, archive, filter_collection_keys, never_collected)
from siliconcompiler.utils.paths import collectiondir
from siliconcompiler.schema.parametervalue import PathNodeValue


needs_symlinks = pytest.mark.skipif(
    sys.platform == "win32", reason="Making a symbolic link needs a privilege on Windows")


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

    import_path = os.path.join(
        collectiondir(proj), PathNodeValue.generate_hashed_collection_path("fake.v", None))

    assert len(os.listdir(collectiondir(proj))) == 1
    with open(import_path, 'r') as f:
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
    with open(import_path, 'r') as f:
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

    import_path = os.path.join(
        collectiondir(proj), PathNodeValue.generate_hashed_collection_path("fake.v", None))

    assert len(os.listdir(collectiondir(proj))) == 1
    with open(import_path, 'r') as f:
        assert f.readline() == 'fake'

    # Remove file, should still be findable in previous collection
    os.remove('fake.v')

    # Rerun collect
    collect(proj, keys=path_keys(proj))
    assert len(os.listdir(collectiondir(proj))) == 1
    with open(import_path, 'r') as f:
        assert f.readline() == 'fake'


def test_collect_same_filename_from_different_directories(path_keys):
    os.makedirs('first', exist_ok=True)
    os.makedirs('second', exist_ok=True)
    with open('first/top.v', 'w') as f:
        f.write('first')
    with open('second/top.v', 'w') as f:
        f.write('second')

    design = Design("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file('first/top.v')
            design.add_file('second/top.v')

    proj = Project(design)
    collect(proj, keys=path_keys(proj))

    for source_dir, expected in (('first', 'first'), ('second', 'second')):
        import_path = os.path.join(
            collectiondir(proj),
            PathNodeValue.generate_hashed_collection_path(f'{source_dir}/top.v', None))
        with open(import_path, 'r') as f:
            assert f.readline() == expected


def test_collect_selects_exact_pernode_value():
    with open('first.tcl', 'w') as f:
        f.write('first')
    with open('second.tcl', 'w') as f:
        f.write('second')

    proj = Project(Design("testdesign"))
    key = ('tool', 'tool0', 'task', 'task0', 'prescript')
    proj.set(*key, 'first.tcl', step='stepone', index='0')
    proj.set(*key, 'second.tcl', step='steptwo', index='0')

    collect(proj, keys=[(key, 'stepone', '0')])

    first_path = os.path.join(
        collectiondir(proj), PathNodeValue.generate_hashed_collection_path('first.tcl', None))
    second_path = os.path.join(
        collectiondir(proj), PathNodeValue.generate_hashed_collection_path('second.tcl', None))
    assert os.path.isfile(first_path)
    assert not os.path.exists(second_path)


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
    """A script that lives inside a refdir should be stored only via the refdir;
    its own hashed path names that copy rather than holding a second one.
    Regression test for sc-issue duplicating OpenROAD scripts that are already
    part of the collected refdir.

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

    new_refdir = PathNodeValue.generate_hashed_collection_path("scripts", None)
    script_collected = PathNodeValue.generate_hashed_collection_path("apr/sc_test.tcl", None)
    assert sorted(os.listdir(custom_collect_dir)) == \
        sorted([new_refdir.split('/')[0], script_collected.split('/')[0]])
    refdir_collected = os.path.join(custom_collect_dir, new_refdir)
    assert os.path.isdir(refdir_collected)
    assert os.path.isfile(os.path.join(refdir_collected, "apr", "sc_test.tcl"))

    # The script's standalone hashed name must NOT be a second copy.
    assert os.path.samefile(os.path.join(custom_collect_dir, script_collected),
                            os.path.join(refdir_collected, "apr", "sc_test.tcl")), \
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

    new_parent = PathNodeValue.generate_hashed_collection_path("parent", None)
    assert os.listdir(collectiondir(proj)) == [new_parent.split('/')[0]]

    child_collected = PathNodeValue.generate_hashed_collection_path("parent/child", None)
    assert not os.path.exists(os.path.join(collectiondir(proj), child_collected)), \
        "Child refdir was copied separately even though parent already covers it"


@pytest.fixture
def two_dataroots():
    """A design where proj/ is dataroot 'top' and proj/rtl/ is dataroot 'rtl', so
    one file is both rtl/a.v under top and a.v under rtl."""
    os.makedirs('proj/rtl/inc')
    with open('proj/rtl/a.v', 'w') as f:
        f.write('a')
    with open('proj/rtl/inc/i.vh', 'w') as f:
        f.write('i')

    design = Design("testdesign")
    design.set_dataroot("top", os.path.abspath("proj"))
    design.set_dataroot("rtl", os.path.abspath("proj/rtl"))
    return design


def _in_collection(proj, paths):
    return all(path.startswith(collectiondir(proj) + os.sep) for path in paths)


def test_collect_file_under_two_dataroots_stored_once(two_dataroots, path_keys):
    design = two_dataroots
    design.add_file("rtl/a.v", dataroot="top", fileset="rtl")
    design.add_file("a.v", dataroot="rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))
    shutil.rmtree("proj")

    files = design.get_file(fileset="rtl", filetype="verilog")
    assert _in_collection(proj, files)
    assert os.path.samefile(files[0], files[1])


def test_collect_file_inside_directory_under_other_dataroot(two_dataroots, path_keys):
    """A file inside a collected directory, but named from another dataroot, is not
    reachable through the directory's collected path, so it must not be skipped."""
    design = two_dataroots
    design.add_idir("rtl", dataroot="top", fileset="rtl")
    design.add_file("a.v", dataroot="rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))
    shutil.rmtree("proj")

    idir = design.get_idir(fileset="rtl")[0]
    files = design.get_file(fileset="rtl", filetype="verilog")
    assert _in_collection(proj, [idir, *files])
    assert os.path.samefile(files[0], os.path.join(idir, "a.v"))


def test_collect_directory_inside_directory_under_other_dataroot(two_dataroots, path_keys):
    design = two_dataroots
    design.add_idir("rtl", dataroot="top", fileset="rtl")
    design.add_idir("inc", dataroot="rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))
    shutil.rmtree("proj")

    idirs = design.get_idir(fileset="rtl")
    assert _in_collection(proj, idirs)
    assert os.listdir(idirs[1]) == ["i.vh"]


def test_collect_absolute_file_inside_collected_directory(two_dataroots, path_keys):
    design = two_dataroots
    design.add_idir("rtl", dataroot="top", fileset="rtl")
    design.add_file(os.path.abspath("proj/rtl/a.v"), fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))
    shutil.rmtree("proj")

    idir = design.get_idir(fileset="rtl")[0]
    files = design.get_file(fileset="rtl", filetype="verilog")
    assert _in_collection(proj, files)
    assert os.path.samefile(files[0], os.path.join(idir, "a.v"))


@needs_symlinks
def test_collect_directory_under_two_dataroots_linked(two_dataroots, path_keys):
    design = two_dataroots
    design.add_idir("rtl", dataroot="top", fileset="rtl")
    design.add_idir(".", dataroot="rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))

    first, second = design.get_idir(fileset="rtl")
    assert not os.path.islink(first)
    assert os.path.islink(second)
    assert os.path.samefile(first, second)


def test_collect_source_beside_collection_with_same_prefix(path_keys):
    """A source whose path starts with the collection's, but is not inside it, is
    still collected."""
    os.makedirs('collected_src')
    with open('collected_src/a.v', 'w') as f:
        f.write('a')

    design = Design("testdesign")
    design.add_file("collected_src/a.v", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj), directory=os.path.abspath("collected"))

    assert os.path.isfile(os.path.join(
        "collected", PathNodeValue.generate_hashed_collection_path("collected_src/a.v", None)))


def test_collect_link_falls_back_to_hard_link(two_dataroots, path_keys, monkeypatch):
    """Without symbolic links, a file named twice is hard-linked and a directory
    named twice is copied, and symbolic links are tried once."""
    symlink = Mock(side_effect=OSError("privilege not held"))
    monkeypatch.setattr(os, "symlink", symlink)

    design = two_dataroots
    design.add_idir("rtl/inc", dataroot="top", fileset="rtl")
    design.add_idir("inc", dataroot="rtl", fileset="rtl")
    design.add_file("rtl/a.v", dataroot="top", fileset="rtl")
    design.add_file("a.v", dataroot="rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))
    shutil.rmtree("proj")

    symlink.assert_called_once()
    idirs = design.get_idir(fileset="rtl")
    files = design.get_file(fileset="rtl", filetype="verilog")
    assert _in_collection(proj, [*idirs, *files])
    assert not os.path.samefile(idirs[0], idirs[1])
    assert os.listdir(idirs[1]) == os.listdir(idirs[0])
    assert not os.path.islink(files[1])
    assert os.path.samefile(files[0], files[1])


def test_collect_link_falls_back_to_copy(two_dataroots, path_keys, monkeypatch):
    monkeypatch.setattr(os, "symlink", Mock(side_effect=OSError("privilege not held")))
    monkeypatch.setattr(os, "link", Mock(side_effect=OSError("not supported")))

    design = two_dataroots
    design.add_file("rtl/a.v", dataroot="top", fileset="rtl")
    design.add_file("a.v", dataroot="rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))
    shutil.rmtree("proj")

    files = design.get_file(fileset="rtl", filetype="verilog")
    assert _in_collection(proj, files)
    assert not os.path.samefile(files[0], files[1])
    for path in files:
        with open(path) as f:
            assert f.read() == 'a'


@needs_symlinks
def test_collect_link_inside_directory_kept(path_keys):
    os.makedirs('rtl')
    with open('rtl/defs.vh', 'w') as f:
        f.write('defs')
    os.symlink('defs.vh', 'rtl/alias.vh')

    design = Design("testdesign")
    design.add_idir("rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))

    idir = design.get_idir(fileset="rtl")[0]
    assert os.readlink(os.path.join(idir, "alias.vh")) == "defs.vh"


@needs_symlinks
def test_collect_link_out_of_directory_stored_once(path_keys):
    """A link's target outside the collection is stored at its first appearance,
    and a later link to it points there, relative, whatever the source link said."""
    os.makedirs('outside')
    with open('outside/ext.vh', 'w') as f:
        f.write('ext')
    os.makedirs('first')
    os.makedirs('second')
    os.symlink(os.path.join('..', 'outside', 'ext.vh'), 'first/ext.vh')
    os.symlink(os.path.abspath('outside/ext.vh'), 'second/ext.vh')

    design = Design("testdesign")
    design.add_idir("first", fileset="rtl")
    design.add_idir("second", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))
    shutil.rmtree('outside')

    first, second = design.get_idir(fileset="rtl")
    assert not os.path.islink(os.path.join(first, "ext.vh"))
    assert not os.path.isabs(os.readlink(os.path.join(second, "ext.vh")))
    with open(os.path.join(second, "ext.vh")) as f:
        assert f.read() == 'ext'


@needs_symlinks
def test_collect_link_to_collected_directory_points_at_its_home(path_keys):
    os.makedirs('a')
    os.makedirs('b')
    with open('b/x.v', 'w') as f:
        f.write('x')
    os.symlink(os.path.join('..', 'b'), 'a/b')

    design = Design("testdesign")
    design.add_idir("a", fileset="rtl")
    design.add_idir("b", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))

    a, b = design.get_idir(fileset="rtl")
    assert not os.path.islink(b)
    assert os.path.islink(os.path.join(a, "b"))
    assert os.path.samefile(os.path.join(a, "b"), b)


@needs_symlinks
def test_collect_link_to_own_directory_kept(path_keys):
    os.makedirs('rtl/inc')
    with open('rtl/inc/i.vh', 'w') as f:
        f.write('i')
    os.symlink('..', 'rtl/inc/up')

    design = Design("testdesign")
    design.add_idir("rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))

    idir = design.get_idir(fileset="rtl")[0]
    assert os.readlink(os.path.join(idir, "inc", "up")) == ".."


@needs_symlinks
def test_collect_link_to_hidden_file_stored(path_keys):
    """A hidden file is left out of a directory, but a link naming it still gets it."""
    os.makedirs('rtl')
    with open('rtl/.defs.vh', 'w') as f:
        f.write('defs')
    os.symlink('.defs.vh', 'rtl/defs.vh')

    design = Design("testdesign")
    design.add_idir("rtl", fileset="rtl")
    proj = Project(design)

    collect(proj, keys=path_keys(proj))

    idir = design.get_idir(fileset="rtl")[0]
    assert os.listdir(idir) == ["defs.vh"]
    assert not os.path.islink(os.path.join(idir, "defs.vh"))


@needs_symlinks
def test_collect_dangling_link_left_out(project_logger, caplog, path_keys):
    os.makedirs('rtl')
    with open('rtl/a.v', 'w') as f:
        f.write('a')
    os.symlink('missing.vh', 'rtl/broken.vh')

    design = Design("testdesign")
    design.add_idir("rtl", fileset="rtl")
    proj = Project(design)
    project_logger(proj)

    collect(proj, keys=path_keys(proj), verbose=False)

    idir = design.get_idir(fileset="rtl")[0]
    assert os.listdir(idir) == ["a.v"]
    assert f"Leaving out {os.path.abspath('rtl/broken.vh')}: its target missing.vh does " \
        "not exist" in caplog.text


@needs_symlinks
def test_collect_links_in_directory_without_symlinks(project_logger, caplog, path_keys,
                                                     monkeypatch):
    """Without symbolic links, a link to a file is a hard link to its copy, a link to
    a directory is a copy made of hard links, and a link to a directory that holds
    it is left out, since the copy would never end."""
    os.makedirs('rtl/inc')
    with open('rtl/defs.vh', 'w') as f:
        f.write('defs')
    with open('rtl/inc/i.vh', 'w') as f:
        f.write('i')
    os.symlink('defs.vh', 'rtl/alias.vh')
    os.symlink('inc', 'rtl/inc_alias')
    os.symlink('..', 'rtl/inc/up')

    design = Design("testdesign")
    design.add_idir("rtl", fileset="rtl")
    proj = Project(design)
    project_logger(proj)

    monkeypatch.setattr(os, "symlink", Mock(side_effect=OSError("privilege not held")))
    collect(proj, keys=path_keys(proj), verbose=False)

    idir = design.get_idir(fileset="rtl")[0]
    alias = os.path.join(idir, "alias.vh")
    assert not os.path.islink(alias)
    assert os.path.samefile(alias, os.path.join(idir, "defs.vh"))
    inc_alias = os.path.join(idir, "inc_alias")
    assert not os.path.islink(inc_alias)
    assert os.path.samefile(os.path.join(inc_alias, "i.vh"),
                            os.path.join(idir, "inc", "i.vh"))
    assert not os.path.lexists(os.path.join(idir, "inc", "up"))
    assert f"Leaving out {os.path.abspath('rtl/inc/up')}: it links to a directory " \
        "that holds it" in caplog.text


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
    path = design.get_idir(fileset="rtl")[0]
    assert os.listdir(path) == []


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
    path = design.get_idir(fileset="rtl")[0]
    assert os.listdir(path) == []


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
    path = design.get_idir(fileset="rtl")[0]
    assert os.listdir(path) == []


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
    path = design.get_idir(fileset="rtl")[0]
    assert os.listdir(path) == []


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


@needs_symlinks
@pytest.mark.parametrize("target_approved", [True, False])
def test_collect_link_to_directory_whitelist(project_logger, caplog, path_keys,
                                             target_approved):
    """A directory a link brings in must be on the whitelist too, or inside a
    directory on it; one that is not is left out."""
    os.makedirs('test')
    os.makedirs('outside/sub')
    with open('outside/sub/ext.v', 'w') as f:
        f.write('ext')
    os.symlink(os.path.join('..', 'outside', 'sub'), 'test/ext')

    design = Design("testdesign")
    design.add_idir("test", fileset="rtl")
    proj = Project(design)
    project_logger(proj)

    whitelist = [os.path.abspath('test')]
    if target_approved:
        whitelist.append(os.path.abspath('outside'))
    collect(proj, keys=path_keys(proj), verbose=False, whitelist=whitelist)

    idir = design.get_idir(fileset="rtl")[0]
    if target_approved:
        assert os.listdir(os.path.join(idir, "ext")) == ["ext.v"]
    else:
        assert os.listdir(idir) == []
        assert f"Leaving out {os.path.abspath('test/ext')}: " \
            f"{os.path.realpath('outside/sub')} is not on the approved collection list" \
            in caplog.text


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


@pytest.mark.parametrize("key,never", [
    (("library", "default", "fileset", "rtl", "file", "verilog"), True),
    (("history", "job0", "option", "builddir"), True),
    (("option", "builddir"), True),
    (("option", "cachedir"), True),
    (("option", "credentials"), True),
    (("tool", "openroad", "task", "place", "input", "place", "0"), True),
    (("tool", "openroad", "task", "place", "output", "place", "0"), True),
    (("tool", "openroad", "task", "place", "report", "place", "0"), True),
    (("tool", "openroad", "task", "place", "script"), False),
    (("library", "gcd", "fileset", "rtl", "file", "verilog"), False),
    (("option", "dir", "rtl"), False),
])
def test_never_collected_is_the_one_rule(key, never):
    """The predicate every caller shares, and what filter_collection_keys
    applies."""
    assert never_collected(key) is never
    assert (filter_collection_keys([(key, None, None)]) == []) is never
