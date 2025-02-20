from core.tools.dummy.dummy import setup as dummy_setup


def setup(chip):
    dummy_setup(chip)
    chip.add('tool', 'dummy', 'task', 'runner', 'output', chip.top() + '.v',
             step='import', index='0')
