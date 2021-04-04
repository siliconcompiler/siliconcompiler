import unittest
from siliconcompiler.core import Chip

class TestCore(unittest.TestCase):

    def test_set_get(self):
        chip = Chip()
        chip.set('target', 'freepdk45')
        self.assertEqual(chip.get('target'), ['freepdk45'])
