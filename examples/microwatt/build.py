#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.package import path as sc_path
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('microwatt')
    chip.set('option', 'entrypoint', 'soc')

    chip.register_source(
        'microwatt',
        'git+https://github.com/antonblanchard/microwatt',
        'd7458d5bebe19d20a6231471b6e0a7823365c2a6')

    chip.add('option', 'define', 'LOG_LENGTH=0')
    chip.add('option', 'define',
             'RAM_INIT_FILE=' + sc_path(chip, 'microwatt') + '/hello_world/hello_world.hex')

    for src in ('decode_types.vhdl',
                'common.vhdl',
                'wishbone_types.vhdl',
                'fetch1.vhdl',
                'utils.vhdl',
                'plru.vhdl',
                'cache_ram.vhdl',
                'icache.vhdl',
                'decode1.vhdl',
                'helpers.vhdl',
                'insn_helpers.vhdl',
                'control.vhdl',
                'decode2.vhdl',
                'register_file.vhdl',
                'cr_file.vhdl',
                'crhelpers.vhdl',
                'ppc_fx_insns.vhdl',
                'rotator.vhdl',
                'logical.vhdl',
                'countzero.vhdl',
                'multiply.vhdl',
                'divider.vhdl',
                'execute1.vhdl',
                'loadstore1.vhdl',
                'mmu.vhdl',
                'dcache.vhdl',
                'writeback.vhdl',
                'core_debug.vhdl',
                'core.vhdl',
                'fpu.vhdl',
                'wishbone_arbiter.vhdl',
                'wishbone_bram_wrapper.vhdl',
                'sync_fifo.vhdl',
                'wishbone_debug_master.vhdl',
                'xics.vhdl',
                'syscon.vhdl',
                'gpio.vhdl',
                'soc.vhdl',
                'spi_rxtx.vhdl',
                'spi_flash_ctrl.vhdl',
                'fpga/soc_reset.vhdl',
                'fpga/pp_fifo.vhd',
                'fpga/pp_soc_uart.vhd',
                'fpga/main_bram.vhdl',
                'nonrandom.vhdl',
                'fpga/clk_gen_ecp5.vhd',
                'fpga/top-generic.vhdl',
                'dmi_dtm_dummy.vhdl'):
        chip.input(src, package='microwatt')

    for src in ('uart16550/uart_top.v',
                'uart16550/uart_regs.v',
                'uart16550/uart_wb.v',
                'uart16550/uart_transmitter.v',
                'uart16550/uart_sync_flops.v',
                'uart16550/uart_receiver.v',
                'uart16550/uart_tfifo.v',
                'uart16550/uart_rfifo.v',
                'uart16550/raminfr.v'):
        chip.input(src, package='microwatt')

    chip.load_target(freepdk45_demo)

    chip.set('tool', 'yosys', 'task', 'syn_asic', 'var', 'autoname', 'false')
    chip.set('tool', 'yosys', 'task', 'syn_asic', 'var', 'flatten', 'false')

    # limit to syn since this example requires a lot of resources
    chip.set('option', 'to', 'syn')

    chip.set('option', 'quiet', True)

    chip.run()


if __name__ == '__main__':
    main()
