import pytest
import tarfile

import os.path

from unittest.mock import patch

from siliconcompiler import Design, Flowgraph, PDK, Project
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.tools.yosys import YosysStdCellLibrary
from siliconcompiler.utils.curation import collect
from siliconcompiler.utils.issue import generate_testcase


NODE_MANIFEST = 'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json'
COLLECT_DIR = 'testcase/build/heartbeat/job0/sc_collected_files'


class TracksPDK(PDK):
    '''PDK exposing a file-typed tool parameter.

    ``openroad,tracks`` mirrors the parameter shape used by the real openroad
    libraries; it is declared here on a PDK to cover the PDK-owned case.
    '''
    def __init__(self, name=None):
        super().__init__(name)
        self.define_tool_parameter("openroad", "tracks", "file",
                                   "The file containing track definitions for routing.")


class RequireLibFilesTask(NOPTask):
    '''Marks the library and PDK owned tool files as required by the task.'''
    def setup(self):
        super().setup()

        self.add_required_key(
            self.project.get("library", "mylib", field="schema"),
            "tool", "yosys", "techmap")
        self.add_required_key(
            self.project.get("library", "mypdk", field="schema"),
            "tool", "openroad", "tracks")


class OtherTask(NOPTask):
    '''A second tool/task pair that the testcase is *not* generated for.'''
    def tool(self):
        return "othertool"

    def task(self):
        return "othertask"


def _write(name, text):
    with open(name, 'w') as f:
        f.write(text)
    return os.path.abspath(name)


@pytest.fixture
def sources():
    '''Creates the source files referenced by the design, library and PDK.'''
    os.makedirs('src', exist_ok=True)
    return {
        'rtl': _write('src/heartbeat.v', 'module heartbeat(); endmodule\n'),
        'techmap': _write('src/techmap.v', '// techmap\n'),
        'tracks': _write('src/tracks.tcl', '# tracks\n'),
        'prescript': _write('src/pre.tcl', '# prescript\n'),
        'otherscript': _write('src/other.tcl', '# other tool prescript\n'),
    }


@pytest.fixture
def project(sources):
    '''A two node project whose library and PDK both own a tool file.'''
    design = Design("heartbeat")
    design.set_dataroot("designroot", os.path.abspath('src'))
    with design.active_fileset("rtl"), design.active_dataroot("designroot"):
        design.set_topmodule("heartbeat")
        design.add_file("heartbeat.v")

    lib = YosysStdCellLibrary()
    lib.set_name("mylib")
    lib.set_dataroot("libroot", os.path.abspath('src'))
    with lib.active_dataroot("libroot"):
        lib.set("tool", "yosys", "techmap", "techmap.v")

    pdk = TracksPDK("mypdk")
    pdk.set_dataroot("pdkroot", os.path.abspath('src'))
    with pdk.active_dataroot("pdkroot"):
        pdk.set("tool", "openroad", "tracks", "tracks.tcl")

    flow = Flowgraph("testflow")
    flow.node("stepone", RequireLibFilesTask())
    flow.node("steptwo", OtherTask())
    flow.edge("stepone", "steptwo")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.add_dep(lib)
    proj.add_dep(pdk)
    proj.set_flow(flow)

    assert proj.run()

    # Reload from the node manifest so the task's require list is populated,
    # which is what sc-issue does.
    return Project.from_manifest(filepath=NODE_MANIFEST)


def make_testcase(proj, **kwargs):
    '''Generates a testcase and returns (archive path, copy flag map).

    The copy flags are snapshotted at collect time, which is after
    generate_testcase() has rewritten every path parameter's copy field.
    '''
    flags = {}

    def record_and_collect(project, **collect_kwargs):
        for keypath in project.allkeys():
            if 'default' in keypath:
                continue
            param = project.get(*keypath, field=None)
            if not param.is_path:
                continue
            flags[','.join(keypath)] = param.get(field='copy')
        return collect(project, **collect_kwargs)

    with patch("siliconcompiler.utils.issue.collect", side_effect=record_and_collect):
        generate_testcase(proj, "stepone", "0",
                          archive_name="testcase.tar.gz",
                          archive_directory=os.getcwd(),
                          verbose_collect=False,
                          **kwargs)

    return os.path.abspath("testcase.tar.gz"), flags


def collected_files(archive):
    '''Returns the basenames collected into the archive's collection directory.'''
    with tarfile.open(archive) as tar:
        return set(
            os.path.basename(name) for name in tar.getnames()
            if os.path.dirname(name) == COLLECT_DIR)


def collected(archive, stem, ext):
    '''Checks the archive for a collected file, which is stored hashed.'''
    return any(name.startswith(f'{stem}_') and name.endswith(ext)
               for name in collected_files(archive))


def test_library_tool_file_copied(project):
    '''A required library owned tool file is copied into the testcase.'''
    archive, flags = make_testcase(project)

    assert flags['library,mylib,tool,yosys,techmap'] is True
    assert collected(archive, 'techmap', '.v')


def test_pdk_tool_file_copied(project):
    '''A required PDK owned tool file is copied into the testcase.'''
    archive, flags = make_testcase(project)

    assert flags['library,mypdk,tool,openroad,tracks'] is True
    assert collected(archive, 'tracks', '.tcl')


def test_library_tool_file_resolves_in_archive(project):
    '''The archived manifest resolves the library file inside the archive.'''
    archive, _ = make_testcase(project)

    with tarfile.open(archive) as tar:
        tar.extractall('replay')

    # Remove the original sources so the only way to resolve the file is
    # through the archive's collection directory.
    os.rename('src', 'src-moved')

    replay_dir = os.path.join('replay', 'testcase')
    cwd = os.getcwd()
    try:
        os.chdir(replay_dir)
        replay = Project.from_manifest(filepath=NODE_MANIFEST)
        techmap = replay.find_files("library", "mylib", "tool", "yosys", "techmap")
        tracks = replay.find_files("library", "mypdk", "tool", "openroad", "tracks")
    finally:
        os.chdir(cwd)

    assert len(techmap) == 1
    for path in (techmap[0], tracks):
        assert os.path.isfile(path)
        assert os.path.dirname(path) == \
            os.path.abspath(os.path.join(replay_dir, 'build/heartbeat/job0/sc_collected_files'))


def test_library_tool_file_excluded_without_libraries(project):
    '''include_libraries=False still gates the library owned tool files.'''
    archive, flags = make_testcase(project, include_libraries=False)

    assert flags['library,mylib,tool,yosys,techmap'] is False
    assert flags['library,mypdk,tool,openroad,tracks'] is False
    assert not collected(archive, 'techmap', '.v')
    assert not collected(archive, 'tracks', '.tcl')


def test_library_tool_file_included_by_specific_library(project):
    '''include_specific_libraries re-enables a single excluded library.'''
    archive, flags = make_testcase(project,
                                   include_libraries=False,
                                   include_specific_libraries=["mylib"])

    assert flags['library,mylib,tool,yosys,techmap'] is True
    assert flags['library,mypdk,tool,openroad,tracks'] is False
    assert collected(archive, 'techmap', '.v')
    assert not collected(archive, 'tracks', '.tcl')


def test_library_tool_file_not_required_not_copied(project, sources):
    '''A library tool file that the task did not require is not copied.'''
    project.set("library", "mylib", "tool", "yosys", "addermap", sources['prescript'])

    archive, flags = make_testcase(project)

    assert flags['library,mylib,tool,yosys,addermap'] is False
    assert not collected(archive, 'pre', '.tcl')


def test_library_fileset_file_still_copied(project, sources):
    '''Library fileset files are unaffected by the tool section handling.'''
    project.set("library", "mylib", "fileset", "rtl", "file", "verilog",
                sources['techmap'])
    project.add("tool", "builtin", "task", "nop", "require",
                "library,mylib,fileset,rtl,file,verilog",
                step="stepone", index="0")

    _, flags = make_testcase(project)

    assert flags['library,mylib,fileset,rtl,file,verilog'] is True


def test_task_files_limited_to_testcase_tool_task(project, sources):
    '''Only the testcase's own tool/task files are copied.'''
    project.set("tool", "builtin", "task", "nop", "prescript", sources['prescript'],
                step="stepone", index="0")
    project.set("tool", "othertool", "task", "othertask", "prescript", sources['otherscript'],
                step="steptwo", index="0")

    archive, flags = make_testcase(project)

    assert flags['tool,builtin,task,nop,prescript'] is True
    assert flags['tool,othertool,task,othertask,prescript'] is False
    assert collected(archive, 'pre', '.tcl')
    assert not collected(archive, 'other', '.tcl')


def test_task_io_files_excluded(project, sources):
    '''input, output and report files are excluded from the testcase.'''
    project.set("tool", "builtin", "task", "nop", "report", "errors", "nop.rpt",
                step="stepone", index="0")

    _, flags = make_testcase(project)

    assert flags['tool,builtin,task,nop,input'] is False
    assert flags['tool,builtin,task,nop,output'] is False
    assert flags['tool,builtin,task,nop,report,errors'] is False


def test_history_and_option_files_excluded(project):
    '''history and the runtime option directories stay excluded.'''
    _, flags = make_testcase(project)

    assert flags['option,builddir'] is False
    assert flags['option,cachedir'] is False
    assert flags['option,credentials'] is False
    assert not any(key.startswith('history,') and value
                   for key, value in flags.items())
