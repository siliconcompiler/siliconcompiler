import unittest
import unittest.mock
from siliconcompiler.core import Chip

class TestCore(unittest.TestCase):

    def test_set_get(self):
        chip = Chip(loglevel='DEBUG')
        chip.set('target', 'freepdk45_asicflow')
        self.assertEqual(chip.get('target'), 'freepdk45_asicflow')

    def test_cli_multi_source(self):
        ''' Regression test for bug where CLI parser wasn't handling multiple
        source files properly.
        '''
        chip = Chip(loglevel='DEBUG')

        args = ['sc', 'examples/ibex/ibex_alu.v', 'examples/ibex/ibex_branch_predict.v', 
                '-target', 'freepdk45_asicflow']
        with unittest.mock.patch('sys.argv', args):
            chip.cmdline('sc')

        assert chip.get('source') == ['examples/ibex/ibex_alu.v', 
                                      'examples/ibex/ibex_branch_predict.v']
        assert chip.get('target') == 'freepdk45_asicflow'
