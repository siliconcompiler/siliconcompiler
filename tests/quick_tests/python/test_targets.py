from siliconcompiler.foundries import asap7, freepdk45, skywater130
from siliconcompiler.core import Chip

# Smoke test that we can initialize all libraries without errors

def test_asap7():
    c = Chip()
    asap7.setup_platform(c)
    asap7.setup_libs(c)
    asap7.setup_methodology(c)

def test_freepdk45():
    c = Chip()
    freepdk45.setup_platform(c)
    freepdk45.setup_libs(c)
    freepdk45.setup_methodology(c)

def test_skywater130():
    c = Chip()
    skywater130.setup_platform(c)
    skywater130.setup_libs(c)
    skywater130.setup_methodology(c)
