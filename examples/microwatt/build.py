import siliconcompiler
import os

microwatt_wd = "../../third_party/designs/microwatt/"

def add_sources(chip):
    chip.add('source', microwatt_wd + 'decode_types.vhdl')
    chip.add('source', microwatt_wd + 'common.vhdl')
    chip.add('source', microwatt_wd + 'wishbone_types.vhdl')
    chip.add('source', microwatt_wd + 'fetch1.vhdl')
    chip.add('source', microwatt_wd + 'utils.vhdl')
    chip.add('source', microwatt_wd + 'plru.vhdl')
    chip.add('source', microwatt_wd + 'cache_ram.vhdl')
    chip.add('source', microwatt_wd + 'icache.vhdl')
    chip.add('source', microwatt_wd + 'decode1.vhdl')
    chip.add('source', microwatt_wd + 'helpers.vhdl')
    chip.add('source', microwatt_wd + 'insn_helpers.vhdl')
    chip.add('source', microwatt_wd + 'control.vhdl')
    chip.add('source', microwatt_wd + 'decode2.vhdl')
    chip.add('source', microwatt_wd + 'register_file.vhdl')
    chip.add('source', microwatt_wd + 'cr_file.vhdl')
    chip.add('source', microwatt_wd + 'crhelpers.vhdl')
    chip.add('source', microwatt_wd + 'ppc_fx_insns.vhdl')
    chip.add('source', microwatt_wd + 'rotator.vhdl')
    chip.add('source', microwatt_wd + 'logical.vhdl')
    chip.add('source', microwatt_wd + 'countzero.vhdl')
    chip.add('source', microwatt_wd + 'multiply.vhdl')
    chip.add('source', microwatt_wd + 'divider.vhdl')
    chip.add('source', microwatt_wd + 'execute1.vhdl')
    chip.add('source', microwatt_wd + 'loadstore1.vhdl')
    chip.add('source', microwatt_wd + 'mmu.vhdl')
    chip.add('source', microwatt_wd + 'dcache.vhdl')
    chip.add('source', microwatt_wd + 'writeback.vhdl')
    chip.add('source', microwatt_wd + 'core_debug.vhdl')
    chip.add('source', microwatt_wd + 'core.vhdl')
    chip.add('source', microwatt_wd + 'fpu.vhdl')
    chip.add('source', microwatt_wd + 'wishbone_arbiter.vhdl')
    chip.add('source', microwatt_wd + 'wishbone_bram_wrapper.vhdl')
    chip.add('source', microwatt_wd + 'sync_fifo.vhdl')
    chip.add('source', microwatt_wd + 'wishbone_debug_master.vhdl')
    chip.add('source', microwatt_wd + 'xics.vhdl')
    chip.add('source', microwatt_wd + 'syscon.vhdl')
    chip.add('source', microwatt_wd + 'gpio.vhdl')
    chip.add('source', microwatt_wd + 'soc.vhdl')
    chip.add('source', microwatt_wd + 'spi_rxtx.vhdl')
    chip.add('source', microwatt_wd + 'spi_flash_ctrl.vhdl')
    chip.add('source', microwatt_wd + 'fpga/soc_reset.vhdl')
    chip.add('source', microwatt_wd + 'fpga/pp_fifo.vhd')
    chip.add('source', microwatt_wd + 'fpga/pp_soc_uart.vhd')
    chip.add('source', microwatt_wd + 'fpga/main_bram.vhdl')
    chip.add('source', microwatt_wd + 'nonrandom.vhdl')
    chip.add('source', microwatt_wd + 'fpga/clk_gen_ecp5.vhd')
    chip.add('source', microwatt_wd + 'fpga/top-generic.vhdl')
    chip.add('source', microwatt_wd + 'dmi_dtm_dummy.vhdl')

def main():
    chip = siliconcompiler.Chip()
    chip.set('design', 'core')
    add_sources(chip)

    cwd = os.getcwd() + '/' + microwatt_wd
    chip.add('define', 'MEMORY_SIZE=8192')
    chip.add('define', 'RAM_INIT_FILE='+cwd+'/hello_world/hello_world.hex')
    chip.add('define', 'RESET_LOW=true')
    chip.add('define', 'CLK_INPUT=50000000')
    chip.add('define', 'CLK_FREQUENCY=40000000')
    chip.load_target('freepdk45_demo')

    # TODO: add in synthesis step once we can get an output that passes thru
    # Yosys.
    flow = 'vhdlsyn'
    chip.node(flow, 'import', 'ghdl')
    chip.node(flow, 'syn', 'yosys')
    chip.edge(flow, 'import', 'syn')

    chip.set('flow', flow)

    chip.run()

if __name__ == '__main__':
    main()
