import os
import siliconcompiler

microwatt_wd = "../../third_party/designs/microwatt/"

def add_sources(chip):
    chip.input(microwatt_wd + 'decode_types.vhdl')
    chip.input(microwatt_wd + 'common.vhdl')
    chip.input(microwatt_wd + 'wishbone_types.vhdl')
    chip.input(microwatt_wd + 'fetch1.vhdl')
    chip.input(microwatt_wd + 'utils.vhdl')
    chip.input(microwatt_wd + 'plru.vhdl')
    chip.input(microwatt_wd + 'cache_ram.vhdl')
    chip.input(microwatt_wd + 'icache.vhdl')
    chip.input(microwatt_wd + 'decode1.vhdl')
    chip.input(microwatt_wd + 'helpers.vhdl')
    chip.input(microwatt_wd + 'insn_helpers.vhdl')
    chip.input(microwatt_wd + 'control.vhdl')
    chip.input(microwatt_wd + 'decode2.vhdl')
    chip.input(microwatt_wd + 'register_file.vhdl')
    chip.input(microwatt_wd + 'cr_file.vhdl')
    chip.input(microwatt_wd + 'crhelpers.vhdl')
    chip.input(microwatt_wd + 'ppc_fx_insns.vhdl')
    chip.input(microwatt_wd + 'rotator.vhdl')
    chip.input(microwatt_wd + 'logical.vhdl')
    chip.input(microwatt_wd + 'countzero.vhdl')
    chip.input(microwatt_wd + 'multiply.vhdl')
    chip.input(microwatt_wd + 'divider.vhdl')
    chip.input(microwatt_wd + 'execute1.vhdl')
    chip.input(microwatt_wd + 'loadstore1.vhdl')
    chip.input(microwatt_wd + 'mmu.vhdl')
    chip.input(microwatt_wd + 'dcache.vhdl')
    chip.input(microwatt_wd + 'writeback.vhdl')
    chip.input(microwatt_wd + 'core_debug.vhdl')
    chip.input(microwatt_wd + 'core.vhdl')
    chip.input(microwatt_wd + 'fpu.vhdl')
    chip.input(microwatt_wd + 'wishbone_arbiter.vhdl')
    chip.input(microwatt_wd + 'wishbone_bram_wrapper.vhdl')
    chip.input(microwatt_wd + 'sync_fifo.vhdl')
    chip.input(microwatt_wd + 'wishbone_debug_master.vhdl')
    chip.input(microwatt_wd + 'xics.vhdl')
    chip.input(microwatt_wd + 'syscon.vhdl')
    chip.input(microwatt_wd + 'gpio.vhdl')
    chip.input(microwatt_wd + 'soc.vhdl')
    chip.input(microwatt_wd + 'spi_rxtx.vhdl')
    chip.input(microwatt_wd + 'spi_flash_ctrl.vhdl')
    chip.input(microwatt_wd + 'fpga/soc_reset.vhdl')
    chip.input(microwatt_wd + 'fpga/pp_fifo.vhd')
    chip.input(microwatt_wd + 'fpga/pp_soc_uart.vhd')
    chip.input(microwatt_wd + 'fpga/main_bram.vhdl')
    chip.input(microwatt_wd + 'nonrandom.vhdl')
    chip.input(microwatt_wd + 'fpga/clk_gen_ecp5.vhd')
    chip.input(microwatt_wd + 'fpga/top-generic.vhdl')
    chip.input(microwatt_wd + 'dmi_dtm_dummy.vhdl')

def main():
    chip = siliconcompiler.Chip('core')
    add_sources(chip)

    cwd = os.getcwd() + '/' + microwatt_wd
    chip.add('option', 'define', 'MEMORY_SIZE=8192')
    chip.add('option', 'define', 'RAM_INIT_FILE=' + cwd + '/hello_world/hello_world.hex')
    chip.add('option', 'define', 'RESET_LOW=true')
    chip.add('option', 'define', 'CLK_INPUT=50000000')
    chip.add('option', 'define', 'CLK_FREQUENCY=40000000')

    chip.load_target("freepdk45_demo")

    # TODO: add in synthesis step once we can get an output that passes thru
    # Yosys.
    flow = 'vhdlsyn'
    chip.node(flow, 'import', 'ghdl')
    chip.node(flow, 'syn', 'yosys')
    chip.edge(flow, 'import', 'syn')

    chip.set('option', 'flow', flow)

    chip.run()

if __name__ == '__main__':
    main()
