import unittest
import unittest.mock
from siliconcompiler.core import Chip

class TestCore(unittest.TestCase):

    def test_set_get(self):
        chip = Chip()
        chip.set('target', 'freepdk45_asicflow')
        self.assertEqual(chip.get('target'), ['freepdk45_asicflow'])

    def test_cli_multi_source(self):
        ''' Regression test for bug where CLI parser wasn't handling multiple
        source files properly.
        '''
        chip = Chip()

        args = ['sc', 'foo.v', 'bar.v', '-target', 'freepdk45_asicflow']
        with unittest.mock.patch('sys.argv', args):
            chip.cmdline()

        assert chip.get('source') == ['foo.v', 'bar.v']
        assert chip.get('target')[-1] == 'freepdk45_asicflow'
