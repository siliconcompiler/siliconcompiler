from siliconcompiler import Chip
from siliconcompiler.design import DesignSchema

from heartbeat import Heartbeat


def test_design_asic():

    c = Chip('heartbeat')
    d = Heartbeat()
    #c.use(Heartbeat)
    #c.run()


def test_design_testbench():
    pass
    #d = setup(scroot)
