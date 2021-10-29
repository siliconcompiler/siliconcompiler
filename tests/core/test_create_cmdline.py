import siliconcompiler

# TODO: find pytest-based way to do mocking
import unittest.mock

def test_cli_multi_source():
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    chip = siliconcompiler.Chip()

    # I think it doesn't matter if these files actually exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc', 'examples/ibex/ibex_alu.v', 'examples/ibex/ibex_branch_predict.v',
            '-target', 'asicflow_freepdk45']

    with unittest.mock.patch('sys.argv', args):
        chip.create_cmdline('sc')

    assert chip.get('source') == ['examples/ibex/ibex_alu.v',
                                  'examples/ibex/ibex_branch_predict.v']
    assert chip.get('target') == 'asicflow_freepdk45'
