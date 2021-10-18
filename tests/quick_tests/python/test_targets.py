from siliconcompiler.pdks import asap7, freepdk45, skywater130
from siliconcompiler.core import Chip

# Smoke test that we can initialize all libraries without errors

def test_asap7():
    c = Chip()
    asap7.setup_pdk(c)

def test_freepdk45():
    c = Chip()
    freepdk45.setup_pdk(c)

def test_skywater130():
    c = Chip()
    skywater130.setup_pdk(c)
