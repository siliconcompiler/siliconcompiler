from core.tools.dummy.dummy import setup as dummy_setup
import os


def setup(chip):
    dummy_setup(chip)


def run(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    var = chip.get('tool', 'dummy', 'task', 'environment', 'var', 'env',
                   step=step, index=index)[0]
    val = chip.get('tool', 'dummy', 'task', 'environment', 'var', 'assert',
                   step=step, index=index)[0]
    assert os.getenv(var) == val

    return 0
