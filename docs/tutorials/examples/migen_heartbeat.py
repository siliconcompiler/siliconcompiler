from migen import *
from migen.fhdl.verilog import convert

import siliconcompiler

class Heartbeat(Module):
  def __init__(self, N=8):
    self.out = Signal()
    self.counter_reg = Signal(N)

    ###

    self.sync += self.counter_reg.eq(self.counter_reg + 1)
    self.sync += self.out.eq(self.counter_reg == Cat(Replicate(0, N-1), 1))

def main():
    heartbeat = Heartbeat()
    convert(heartbeat, ios={heartbeat.out}, name='heartbeat').write('heartbeat.v')

    chip = siliconcompiler.Chip()
    chip.set('source', 'heartbeat.v')
    chip.set('design', 'heartbeat')
    # default Migen clock pin is named 'sys_clk'
    chip.clock(name='sys', pin='sys_clk', period=1)
    chip.load_target('freepdk45_demo')
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
