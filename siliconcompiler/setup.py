#FREEPDK45
from foundry.virtual.freepdk45.pdk.sc_pdk import setup_freepdk45_pdk
from foundry.virtual.freepdk45.libs.sc_libs import setup_freepdk45_libs

#ASAP7
from foundry.virtual.asap7.pdk.sc_pdk import setup_asap7_pdk
from foundry.virtual.asap7.libs.sc_libs import setup_asap7_libs

#SKYWATER130
from foundry.skywater.skywater130.pdk.sc_pdk import setup_skywater130_pdk
from foundry.skywater.skywater130.libs.sc_libs import setup_skywater130_libs

#EDA
from eda.klayout.klayout import setup_klayout
from eda.yosys.yosys import setup_yosys
from eda.openroad.openroad import setup_openroad
from eda.verilator.verilator import setup_verilator

#Setup Method Called from CLI
def setup_open(chip, target):

    #PDK Setup
    if target == 'freepdk45': 
        setup_freepdk45_pdk(chip)
        setup_freepdk45_libs(chip)
    elif target == 'asap7':
        setup_asap7_pdk(chip)
        setup_asap7_libs(chip)
    elif target == 'skywater130':
        setup_skywater130_pdk(chip)
        setup_skywater130_libs(chip)    

    #EDA Setup
    setup_verilator(chip)
    setup_yosys(chip)
    setup_openroad(chip)
    setup_klayout(chip)
