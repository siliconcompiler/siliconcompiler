import siliconcompiler
from siliconcompiler._common import SiliconCompilerError

import pytest
import os
import logging

import tests.core.tools.run.run as run


@pytest.mark.parametrize("quiet", [True, False])
def test(datadir, capfd, quiet):

    chip = siliconcompiler.Chip('test')
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    flow = siliconcompiler.Flow(chip, "testflow")
    flow.node("testflow", "run", run)

    chip.use(flow)
    chip.set("option", "flow", "testflow")

    chip.set("option", "quiet", quiet)

    chip.set("tool", "run", "task", "run", "option",
             os.path.join(datadir, "failing_tool.sh"),
             step="run", index=0)

    # We expect the run to fail
    try:
        chip.run()
    except SiliconCompilerError:
        ...

    output = capfd.readouterr()
    assert "UnicodeDecodeError" not in output.err
