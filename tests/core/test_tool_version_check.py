from siliconcompiler import Chip
from siliconcompiler.scheduler import _check_tool_version
from core.tools.fake import fake_out, fake
import os
import pytest
import sys


@pytest.mark.skipif(sys.platform == 'win32', reason='Bash not available')
def test_check_tool_version_failed_error_code():
    with open('tool.sh', 'w') as f:
        f.write('#!/usr/bin/env bash\n')
        f.write('echo "VERSION FAILED"\n')
        f.write('exit 1\n')

    os.chmod('tool.sh', 0x777)

    chip = Chip('test')
    chip.node('test', 'test', fake_out)
    chip.set('tool', 'fake', 'exe', os.path.abspath('tool.sh'))
    chip.set('tool', 'fake', 'vswitch', '-ver')
    chip.set('tool', 'fake', 'version', '>=1.0.0')
    chip._add_file_logger('test.log')

    def parse_version(stdout):
        return stdout.strip()
    setattr(fake, 'parse_version', parse_version)

    chip.set('option', 'flow', 'test')

    with pytest.raises(SystemExit):
        _check_tool_version(chip, 'test', '0')

    with open('test.log') as f:
        assert "Tool 'tool.sh' responded with: VERSION FAILED" in f.read()


@pytest.mark.skipif(sys.platform == 'win32', reason='Bash not available')
def test_check_tool_version_failed():
    with open('tool.sh', 'w') as f:
        f.write('#!/usr/bin/env bash\n')
        f.write('echo "VERSION FAILED"\n')
        f.write('exit 0\n')

    os.chmod('tool.sh', 0x777)

    chip = Chip('test')
    chip.node('test', 'test', fake_out)
    chip.set('tool', 'fake', 'exe', os.path.abspath('tool.sh'))
    chip.set('tool', 'fake', 'vswitch', '-ver')
    chip.set('tool', 'fake', 'version', '>=1.0.0')
    chip._add_file_logger('test.log')

    def parse_version(stdout):
        return stdout.strip()
    setattr(fake, 'parse_version', parse_version)

    chip.set('option', 'flow', 'test')

    with pytest.raises(SystemExit):
        _check_tool_version(chip, 'test', '0')

    with open('test.log') as f:
        assert "Tool 'tool.sh' responded with: VERSION FAILED" not in f.read()
