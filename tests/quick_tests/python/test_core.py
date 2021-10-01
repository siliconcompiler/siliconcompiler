import unittest
import unittest.mock
from siliconcompiler.core import Chip

class TestCore(unittest.TestCase):

    def test_set_get(self):
        chip = Chip(loglevel='DEBUG')
        chip.set('target', 'asicflow_freepdk45')
        self.assertEqual(chip.get('target'), 'asicflow_freepdk45')

    def test_cli_multi_source(self):
        ''' Regression test for bug where CLI parser wasn't handling multiple
        source files properly.
        '''
        chip = Chip(loglevel='DEBUG')

        args = ['sc', 'examples/ibex/ibex_alu.v', 'examples/ibex/ibex_branch_predict.v',
                '-target', 'asicflow_freepdk45']
        with unittest.mock.patch('sys.argv', args):
            chip.create_cmdline('sc')

        assert chip.get('source') == ['examples/ibex/ibex_alu.v',
                                      'examples/ibex/ibex_branch_predict.v']
        assert chip.get('target') == 'asicflow_freepdk45'
