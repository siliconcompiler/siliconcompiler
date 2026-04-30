import os
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.apps import sc_show
from siliconcompiler.utils.paths import workdir, jobdir


@pytest.fixture
def make_manifests():
    def impl(project):
        for nodes in project.get("flowgraph", "asicflow", field="schema").get_execution_order():
            for step, index in nodes:
                for d in ('inputs', 'outputs'):
                    path = os.path.join(workdir(project, step=step, index=index), d)
                    os.makedirs(path, exist_ok=True)
                    project.write_manifest(os.path.join(path, f"{project.name}.pkg.json"))
        project.write_manifest(os.path.join(jobdir(project),
                                            f"{project.name}.pkg.json"))

    return impl


@pytest.mark.timeout(90)
@pytest.mark.parametrize('flags', [
    [],
    ['-design', 'gcd'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0'],
    ['-design', 'gcd']
])
def test_sc_show_design_only(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool=None, open=False)


@pytest.mark.timeout(90)
@pytest.mark.parametrize('flags', [
    [],
    ['-design', 'gcd'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0'],
])
def test_sc_show_design_only_screenshot(flags, monkeypatch, make_manifests, asic_gcd, capsys):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    with open("test.png", "w") as f:
        f.write("test")

    monkeypatch.setattr('sys.argv', ['sc-show', '-screenshot'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        show.return_value = "test.png"
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=True, tool=None, open=False)
    assert "Screenshot file: test.png" in capsys.readouterr().out


@pytest.mark.parametrize('flags', [
    ['build/gcd/job0/route.detailed/0/outputs/gcd.def'],
    ['build/gcd/job0/route.detailed/0/outputs/gcd.def'],
    ['build/gcd/job0/write.gds/0/outputs/gcd.gds'],
    ['build/gcd/job0/write.gds/0/inputs/gcd.def',
     '-cfg', 'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json']
])
def test_sc_show(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(flags[0], extension=None, screenshot=False, tool=None, open=False)


def test_sc_show_double_flags(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', 'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json',
                                     '-cfg', 'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json'])
    assert sc_show.main() == 1


@pytest.mark.timeout(90)
@pytest.mark.parametrize('flags', [
    ['-design', 'gcd'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0'],
])
def test_sc_show_design_only_open(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with -open flag.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-open'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool=None, open=True)


@pytest.mark.timeout(90)
def test_sc_show_open_with_file(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show -open with a file path.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show',
                                     'build/gcd/job0/write.gds/0/outputs/gcd.def',
                                     '-open'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with('build/gcd/job0/write.gds/0/outputs/gcd.def',
                                     extension=None, screenshot=False, tool=None, open=True)


@pytest.mark.timeout(90)
def test_sc_show_open_with_tool_and_extension(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show -open with -tool and -ext.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-open',
                                     '-ext', 'odb', '-tool', 'openroad'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension='odb', screenshot=False,
                                     tool='openroad', open=True)


@pytest.mark.timeout(90)
def test_sc_show_open_and_screenshot_mutually_exclusive(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show errors when both -open and -screenshot are specified.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-open', '-screenshot'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 1
        show.assert_not_called()


@pytest.mark.timeout(90)
def test_sc_show_with_tool_design_only(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and design only.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='klayout', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_file(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and file path.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', 'build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     '-tool', 'openlane'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with('build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     extension=None, screenshot=False, tool='openlane', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_screenshot(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and screenshot.'''
    make_manifests(asic_gcd)

    with open("test.png", "w") as f:
        f.write("test")

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-screenshot',
                                     '-tool', 'gds2png'])
    with patch('siliconcompiler.Project.show') as show:
        show.return_value = "test.png"
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=True, tool='gds2png', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_extension(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and file extension.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-ext', 'odb',
                                     '-tool', 'openroad'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension='odb', screenshot=False, tool='openroad', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_step_index(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and step/index parameters.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-arg_step', 'route.detailed',
                                     '-arg_index', '0', '-tool', 'magic'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='magic', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_jobname(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and jobname.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-jobname', 'rtl2gds',
                                     '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='klayout', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_cfg(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and configuration file.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-cfg',
                                     'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json',
                                     '-tool', 'magic'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='magic', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_empty_tool(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with empty tool string.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-tool', ''])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='', open=False)


# Mock task classes for testing
class MockShowTask1:
    """Mock show task for testing."""
    def tool(self):
        return "tool1"

    def task(self):
        return "task1"

    def get_supported_task_extentions(self):
        return ["ext1", "ext2"]


class MockShowTask2:
    """Mock show task for testing."""
    def tool(self):
        return "tool2"

    def task(self):
        return "task2"

    def get_supported_task_extentions(self):
        return ["ext3"]


class MockScreenshotTask1:
    """Mock screenshot task for testing."""
    def tool(self):
        return "tool1"

    def task(self):
        return "screenshot1"

    def get_supported_task_extentions(self):
        return ["ext1", "ext2"]


class MockScreenshotTask2:
    """Mock screenshot task for testing."""
    def tool(self):
        return "tool2"

    def task(self):
        return "screenshot2"

    def get_supported_task_extentions(self):
        return ["ext3"]


class MockOpenTask1:
    """Mock open task for testing."""
    def tool(self):
        return "tool1"

    def task(self):
        return "open1"

    def get_supported_task_extentions(self):
        return ["ext1", "ext2"]


class MockOpenTask2:
    """Mock open task for testing."""
    def tool(self):
        return "tool2"

    def task(self):
        return "open2"

    def get_supported_task_extentions(self):
        return ["ext3"]


@pytest.mark.timeout(90)
def test_sc_show_list_show_tools(monkeypatch, capsys):
    '''Test sc-show -list to display show tools.'''
    monkeypatch.setattr('sys.argv', ['sc-show', '-list'])

    mock_tasks = [MockShowTask1, MockShowTask2]

    with patch('siliconcompiler.apps.sc_show.ShowTask.get_task') as mock_get_task:
        mock_get_task.return_value = mock_tasks
        assert sc_show.main() == 0

    captured = capsys.readouterr()
    output = captured.out

    # Verify header and structure
    assert "Registered Show Tools (in order):" in output
    assert "=" * 70 in output

    # Verify tools are listed with their extensions
    assert "1. tool1/task1" in output
    assert "Extensions: ext1, ext2" in output
    assert "2. tool2/task2" in output
    assert "Extensions: ext3" in output


@pytest.mark.timeout(90)
def test_sc_show_list_screenshot_tools(monkeypatch, capsys):
    '''Test sc-show -list -screenshot to display screenshot tools.'''
    monkeypatch.setattr('sys.argv', ['sc-show', '-list', '-screenshot'])

    mock_tasks = [MockScreenshotTask1, MockScreenshotTask2]

    with patch('siliconcompiler.apps.sc_show.ScreenshotTask.get_task') as mock_get_task:
        mock_get_task.return_value = mock_tasks
        assert sc_show.main() == 0

    captured = capsys.readouterr()
    output = captured.out

    # Verify header and structure
    assert "Registered Screenshot Tools (in order):" in output
    assert "=" * 70 in output

    # Verify tools are listed with their extensions
    assert "1. tool1/screenshot1" in output
    assert "Extensions: ext1, ext2" in output
    assert "2. tool2/screenshot2" in output
    assert "Extensions: ext3" in output


@pytest.mark.timeout(90)
def test_sc_show_list_open_tools(monkeypatch, capsys):
    '''Test sc-show -list -open to display open tools.'''
    monkeypatch.setattr('sys.argv', ['sc-show', '-list', '-open'])

    mock_tasks = [MockOpenTask1, MockOpenTask2]

    with patch('siliconcompiler.apps.sc_show.OpenTask.get_task') as mock_get_task:
        mock_get_task.return_value = mock_tasks
        assert sc_show.main() == 0

    captured = capsys.readouterr()
    output = captured.out

    # Verify header and structure
    assert "Registered Open Tools (in order):" in output
    assert "=" * 70 in output

    # Verify tools are listed with their extensions
    assert "1. tool1/open1" in output
    assert "Extensions: ext1, ext2" in output
    assert "2. tool2/open2" in output
    assert "Extensions: ext3" in output


@pytest.mark.timeout(90)
def test_sc_show_list_empty_tools(monkeypatch, capsys):
    '''Test sc-show -list when no tools are registered.'''
    monkeypatch.setattr('sys.argv', ['sc-show', '-list'])

    with patch('siliconcompiler.apps.sc_show.ShowTask.get_task') as mock_get_task:
        mock_get_task.return_value = None
        assert sc_show.main() == 0

    captured = capsys.readouterr()
    output = captured.out

    # When no tasks, should still return 0 with no output
    assert "Registered Show Tools (in order):" not in output


@pytest.mark.timeout(90)
def test_sc_show_list_single_tool(monkeypatch, capsys):
    '''Test sc-show -list with a single tool.'''
    monkeypatch.setattr('sys.argv', ['sc-show', '-list'])

    mock_tasks = [MockShowTask1]

    with patch('siliconcompiler.apps.sc_show.ShowTask.get_task') as mock_get_task:
        mock_get_task.return_value = mock_tasks
        assert sc_show.main() == 0

    captured = capsys.readouterr()
    output = captured.out

    # Verify correct numbering starts at 1
    assert "1. tool1/task1" in output
    assert "2. tool" not in output  # Should not have a second tool


@pytest.mark.timeout(90)
def test_sc_show_list_sorted_extensions(monkeypatch, capsys):
    '''Test sc-show -list displays extensions in sorted order.'''
    monkeypatch.setattr('sys.argv', ['sc-show', '-list'])

    class MockTaskWithUnsortedExts:
        def tool(self):
            return "tool"

        def task(self):
            return "task"

        def get_supported_task_extentions(self):
            # Return unsorted extensions
            return ["zed", "abc", "mno"]

    mock_tasks = [MockTaskWithUnsortedExts]

    with patch('siliconcompiler.apps.sc_show.ShowTask.get_task') as mock_get_task:
        mock_get_task.return_value = mock_tasks
        assert sc_show.main() == 0

    captured = capsys.readouterr()
    output = captured.out

    # Verify extensions are sorted alphabetically
    assert "Extensions: abc, mno, zed" in output


@pytest.mark.timeout(90)
def test_sc_show_list_no_extensions(monkeypatch, capsys):
    '''Test sc-show -list with a tool that has no supported extensions.'''
    monkeypatch.setattr('sys.argv', ['sc-show', '-list'])

    class MockTaskNoExts:
        def tool(self):
            return "tool"

        def task(self):
            return "task"

        def get_supported_task_extentions(self):
            return []

    mock_tasks = [MockTaskNoExts]

    with patch('siliconcompiler.apps.sc_show.ShowTask.get_task') as mock_get_task:
        mock_get_task.return_value = mock_tasks
        assert sc_show.main() == 0

    captured = capsys.readouterr()
    output = captured.out

    # Verify "none" is shown for no extensions
    assert "Extensions: none" in output


@pytest.mark.timeout(90)
def test_sc_show_tool_with_all_parameters(monkeypatch, make_manifests, asic_gcd, capsys):
    '''Test sc-show app with tool and multiple other parameters.'''
    make_manifests(asic_gcd)

    with open("test.png", "w") as f:
        f.write("test")

    monkeypatch.setattr('sys.argv', ['sc-show', 'build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     '-ext', 'gds', '-screenshot', '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        show.return_value = "test.png"
        assert sc_show.main() == 0
        show.assert_called_once_with('build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     extension='gds', screenshot=True, tool='klayout', open=False)
    assert "Screenshot file: test.png" in capsys.readouterr().out


@pytest.mark.timeout(90)
def test_sc_show_with_tool_task_format(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool/task format.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-tool', 'klayout/full'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='klayout/full', open=False)


@pytest.mark.timeout(90)
def test_sc_show_with_tool_task_and_extension(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool/task format and extension.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-ext', 'gds',
                                     '-tool', 'openroad/timing'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension='gds', screenshot=False,
                                     tool='openroad/timing', open=False)


@pytest.mark.parametrize('flags', [
    ['-ext', 'gds'],
    ['-design', 'gcd', '-ext', 'gds'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init', '-ext', 'def'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0', '-ext', 'odb'],
])
def test_sc_show_ext(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=flags[-1], screenshot=False, tool=None, open=False)


def test_sc_show_no_manifest(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'test', '-arg_step', 'invalid'])
    assert sc_show.main() == 1


@pytest.mark.timeout(90)
def test_sc_show_file_without_manifest_no_design(monkeypatch):
    '''Test sc-show with file but no manifest and no design specified.'''
    # Create a test file
    test_file = 'test_no_design.gds'
    with open(test_file, 'w') as f:
        f.write('test content')

    monkeypatch.setattr('sys.argv', ['sc-show', test_file])
    # Design will be inferred from filename, so should succeed
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(test_file, extension=None, screenshot=False, tool=None, open=False)


@pytest.mark.timeout(90)
def test_sc_show_file_without_manifest_with_design(monkeypatch):
    '''Test sc-show with file but no manifest, with design specified.'''
    # Create a test file
    test_file = 'test_with_design.gds'
    with open(test_file, 'w') as f:
        f.write('test content')

    monkeypatch.setattr('sys.argv', ['sc-show', test_file, '-design', 'mydesign'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        # Should be called with the file path
        show.assert_called_once_with(test_file, extension=None, screenshot=False, tool=None, open=False)


@pytest.mark.timeout(90)
def test_sc_show_file_without_manifest_with_extension(monkeypatch):
    '''Test sc-show with file, no manifest, but with extension specified.'''
    # Create a test file
    test_file = 'test_ext.def'
    with open(test_file, 'w') as f:
        f.write('test content')

    monkeypatch.setattr('sys.argv', ['sc-show', test_file, '-design', 'test',
                                     '-ext', 'def'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(test_file, extension='def', screenshot=False, tool=None, open=False)


@pytest.mark.timeout(90)
def test_sc_show_file_without_manifest_with_tool(monkeypatch):
    '''Test sc-show with file, no manifest, but with tool specified.'''
    # Create a test file
    test_file = 'test_tool.gds'
    with open(test_file, 'w') as f:
        f.write('test content')

    monkeypatch.setattr('sys.argv', ['sc-show', test_file, '-design', 'test',
                                     '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(test_file, extension=None,
                                     screenshot=False, tool='klayout', open=False)


@pytest.mark.timeout(90)
def test_sc_show_file_without_manifest_with_tool_task(monkeypatch):
    '''Test sc-show with file, no manifest, with tool/task format.'''
    # Create a test file
    test_file = 'test_tool_task.gds'
    with open(test_file, 'w') as f:
        f.write('test content')

    monkeypatch.setattr('sys.argv', ['sc-show', test_file, '-design', 'test',
                                     '-tool', 'klayout/show'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(test_file, extension=None, screenshot=False,
                                     tool='klayout/show', open=False)


@pytest.mark.timeout(90)
def test_sc_show_file_without_manifest_with_all_args(monkeypatch):
    '''Test sc-show with file, no manifest, and all arguments specified.'''
    # Create a test file
    test_file = 'test_all_args.def'
    with open(test_file, 'w') as f:
        f.write('test content')

    monkeypatch.setattr('sys.argv', ['sc-show', test_file, '-design', 'mydesign',
                                     '-ext', 'def', '-tool', 'openroad/show'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(test_file, extension='def', screenshot=False,
                                     tool='openroad/show', open=False)


@pytest.mark.timeout(90)
def test_sc_show_file_without_manifest_with_screenshot(monkeypatch):
    '''Test sc-show with file, no manifest, and screenshot flag.'''
    # Create a test file
    test_file = 'test_screenshot.gds'
    with open(test_file, 'w') as f:
        f.write('test content')

    with open("test.png", "w") as f:
        f.write("test")

    monkeypatch.setattr('sys.argv', ['sc-show', test_file, '-design', 'test',
                                     '-screenshot', '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        show.return_value = "test.png"
        assert sc_show.main() == 0
        show.assert_called_once_with(test_file, extension=None, screenshot=True,
                                     tool='klayout', open=False)


@pytest.mark.timeout(90)
def test_sc_show_nonexistent_file_with_design(monkeypatch):
    '''Test sc-show with non-existent file and design specified.'''
    nonexistent_file = "/tmp/nonexistent_file_12345.gds"

    monkeypatch.setattr('sys.argv', ['sc-show', nonexistent_file, '-design', 'test'])
    with patch('siliconcompiler.Project.show') as show:
        # Should still attempt to show even with non-existent file
        # (the actual file existence check happens in project.show())
        assert sc_show.main() == 0
        show.assert_called_once_with(nonexistent_file, extension=None, screenshot=False, tool=None, open=False)
