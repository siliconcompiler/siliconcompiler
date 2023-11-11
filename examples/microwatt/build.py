import siliconcompiler


def add_sources(chip):
    chip.register_package_source('microwatt',
                                 'git+https://github.com/antonblanchard/microwatt',
                                 'd7458d5bebe19d20a6231471b6e0a7823365c2a6')
    chip.input('decode_types.vhdl', package='microwatt')
    chip.input('common.vhdl', package='microwatt')
    chip.input('wishbone_types.vhdl', package='microwatt')
    chip.input('fetch1.vhdl', package='microwatt')
    chip.input('utils.vhdl', package='microwatt')
    chip.input('plru.vhdl', package='microwatt')
    chip.input('cache_ram.vhdl', package='microwatt')
    chip.input('icache.vhdl', package='microwatt')
    chip.input('decode1.vhdl', package='microwatt')
    chip.input('helpers.vhdl', package='microwatt')
    chip.input('insn_helpers.vhdl', package='microwatt')
    chip.input('control.vhdl', package='microwatt')
    chip.input('decode2.vhdl', package='microwatt')
    chip.input('register_file.vhdl', package='microwatt')
    chip.input('cr_file.vhdl', package='microwatt')
    chip.input('crhelpers.vhdl', package='microwatt')
    chip.input('ppc_fx_insns.vhdl', package='microwatt')
    chip.input('rotator.vhdl', package='microwatt')
    chip.input('logical.vhdl', package='microwatt')
    chip.input('countzero.vhdl', package='microwatt')
    chip.input('multiply.vhdl', package='microwatt')
    chip.input('divider.vhdl', package='microwatt')
    chip.input('execute1.vhdl', package='microwatt')
    chip.input('loadstore1.vhdl', package='microwatt')
    chip.input('mmu.vhdl', package='microwatt')
    chip.input('dcache.vhdl', package='microwatt')
    chip.input('writeback.vhdl', package='microwatt')
    chip.input('core_debug.vhdl', package='microwatt')
    chip.input('core.vhdl', package='microwatt')
    chip.input('fpu.vhdl', package='microwatt')
    chip.input('wishbone_arbiter.vhdl', package='microwatt')
    chip.input('wishbone_bram_wrapper.vhdl', package='microwatt')
    chip.input('sync_fifo.vhdl', package='microwatt')
    chip.input('wishbone_debug_master.vhdl', package='microwatt')
    chip.input('xics.vhdl', package='microwatt')
    chip.input('syscon.vhdl', package='microwatt')
    chip.input('gpio.vhdl', package='microwatt')
    chip.input('soc.vhdl', package='microwatt')
    chip.input('spi_rxtx.vhdl', package='microwatt')
    chip.input('spi_flash_ctrl.vhdl', package='microwatt')
    chip.input('fpga/soc_reset.vhdl', package='microwatt')
    chip.input('fpga/pp_fifo.vhd', package='microwatt')
    chip.input('fpga/pp_soc_uart.vhd', package='microwatt')
    chip.input('fpga/main_bram.vhdl', package='microwatt')
    chip.input('nonrandom.vhdl', package='microwatt')
    chip.input('fpga/clk_gen_ecp5.vhd', package='microwatt')
    chip.input('fpga/top-generic.vhdl', package='microwatt')
    chip.input('dmi_dtm_dummy.vhdl', package='microwatt')


def main():
    chip = siliconcompiler.Chip('core')
    add_sources(chip)

    chip.add('option', 'define', 'MEMORY_SIZE=8192')
    # chip.add('option', 'define', 'RAM_INIT_FILE=' + cwd + '/hello_world/hello_world.hex')
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
