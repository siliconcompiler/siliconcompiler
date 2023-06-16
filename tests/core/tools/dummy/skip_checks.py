from siliconcompiler.tools import SkipCheck


def setup(chip):
    chip.set('tool', 'dummy', 'task', 'skip_checks', 'option', [])


def skip_checks(chip):
    return SkipCheck
