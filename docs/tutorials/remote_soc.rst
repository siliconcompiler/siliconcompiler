Building Your Own SoC
=====================

SiliconCompiler supports a "zero-install" remote workflow, which lets you write hardware designs on your local machine and build them on cloud servers. We are currently running a free public beta, and the :ref:`remote API <Server API>` is a simple collection of HTTP requests which we publish under an open-source license.

You can use the remote flow to try SiliconCompiler or experiment with hardware design, without going through the trouble of building and installing a full suite of open-source EDA tools on your local machine. This tutorial will walk you through the process of building an ASIC containing one PicoRV32 RISC-V CPU core and 2 kilobytes of SRAM, on an open-source 130nm Skywater process node.

Note that our public beta currently only supports open-source tools and PDKs. You can access the public beta without a signup or login, and it is designed to delete your data after your jobs finish, but it is not intended to process proprietary or restricted intellectual property! Please `review our terms of service <https://www.siliconcompiler.com/terms-of-service>`_, and do not submit IP which you are not allowed to distribute.

You can find complete example designs which reflect the contents of this tutorial in the public SiliconCompiler repository, `with RAM <https://github.com/siliconcompiler/siliconcompiler/tree/main/examples/picorv32_ram>`_ and `without RAM <https://github.com/siliconcompiler/siliconcompiler/tree/main/examples/picorv32>`_.

[TODO / CR feedback: Add a screenshot here (or at the bottom)?]

Installing SiliconCompiler
--------------------------

You must have a recent version of Python3 and its Pip package manager in order to install SiliconCompiler. We recommend that Windows users download Python from `https://python.org/downloads/ <https://python.org/downloads/>`_, rather than the Microsoft Store.

With that, you should be able to install SiliconCompiler directly from PyPi::

    pip install siliconcompiler

If you are using an older operating system which includes Python2 as a default, you may need to run::

    pip3 install siliconcompiler

(TODO: Windows check)

If the installation was successful, you should be able to check which version you have with ``sc -version``::

    $ sc -version
    0.9.6

Finally, in order to access the cloud beta, you need to tell SiliconCompiler where your remote server is located. We do not currently require login credentials for our public open-source server, so you can simply run::

    sc-configure https://server.siliconcompiler.com

(Optional) Testing SiliconCompiler
----------------------------------

Before we start building an SoC, you can run a quick example from the command line to check that everything is working::

    echo "module heartbeat #(parameter N = 8)
       (input clk, input nreset, output reg out);
       reg [N-1:0] counter_reg;
       always @ (posedge clk or negedge nreset)
         if(!nreset) begin
            counter_reg <= 'b0;
            out <= 1'b0;
         end else begin
            counter_reg[N-1:0] <= counter_reg[N-1:0] + 1'b1;
            out <= (counter_reg[N-1:0]=={(N){1'b1}});
         end
    endmodule" > heartbeat.v
    echo "create_clock -name clk -period 10 [get_ports {clk}]" > heartbeat.sdc
    
    sc heartbeat.v heartbeat.sdc -design heartbeat -target freepdk45_demo -remote

The job should take a few minutes to run, printing the run's status periodically. After it completes, you should see a table of metrics printed in the command line, and you can find a screenshot of the final GDS-II results at [TODO: serverside KLayout screenshot location after export/0].

Download PicoRV32 Verilog Code
------------------------------

The heart of any digital design is its HDL code, typically written in a language such as Verilog or VHDL. High-level synthesis languages are gaining in popularity, but most of them still output their final design sources in a traditional HDL such as Verilog.

PicoRV32 is an open-source implementation of a small RISC-V CPU core, the sort you might find in a low-power microcontroller. Its source code, license, and various tooling can be found `in its GitHub repository <https://github.com/YosysHQ/picorv32>`_.

The repository contains many files, but the core CPU design is located in a single file called ``picorv32.v`` at the root of the repository.

Create a new directory for this project, and copy the ``picorv32.v`` file into it.

Because we are building this design as an ASIC rather than an FPGA bitstream, you will also need a constraints file to set a reference for the core clock signal. Create a file called ``picorv32.sdc`` in your new build directory, containing the following line::

    create_clock -name clk -period 10 [get_ports {clk}]

Build the PicoRV32 Core using SiliconCompiler
---------------------------------------------

Before we add the complexity of a RAM macro block, let's build the core design using the open-source Skywater130 PDK. Copy the following build script into the same directory which you copied ``picorv32.v`` into::

    import siliconcompiler

    chip = siliconcompiler.Chip('picorv32')
    chip.load_target('skywater130_demo')
    chip.input('picorv32.v')
    chip.set('option', 'remote', True)
    chip.run()

If you run that example as a Python script, it should take approximately 10-15 minutes to run if the servers are not too busy. We have not added a RAM macro yet, but this script will build the CPU core with I/O signals placed pseudo-randomly around the edges of the die area. Once the job finishes, you should receive a screenshot of your final design, and a report containing metrics related to the build.

For the full GDS-II results and intermediate build artifacts, you can install the EDA tools on your local system, and run the same Python build script with the :keypath:`option, remote` parameter set to ``False``. We are not returning the full results during this early beta period because we want to minimize bandwidth, and we believe that the open-source tools/PDKs are currently best suited for rapid prototyping and design exploration.

Adding an SRAM block
--------------------

A CPU core is not very useful without any memory. Indeed, a real system-on-chip would need quite a few supporting IP blocks to be useful in the real world. At the very least, you would want a SPI interface for communicating with external non-volatile memory, a UART to get data in and out of the core, a debugging interface, and a small on-die cache.

In this tutorial, we'll take the first step by adding a small (2 kilobyte) SRAM block and wiring it to the CPU's memory interface. This will teach you how to import and place a hard IP block in your design.

The open-source Skywater130 PDK does not currently include foundry-published memory macros. Instead, they have a set of OpenRAM configurations which are blessed by the maintainers. You can use `those configurations <https://github.com/VLSIDA/OpenRAM/tree/stable/technology/sky130>`_ to generate RAM macros from scratch if you are willing to install the `OpenRAM utility <https://github.com/VLSIDA/OpenRAM>`_, or you can `download pre-built files <https://github.com/VLSIDA/sky130_sram_macros>`_ which have been published under a permissive license. We will use the ``sky130_sram_2kbyte_1rw1r_32x512_8`` block in this example.

Once you have a GDS and LEF file for your RAM macro, create a new directory called ``sram`` in same location as your PicoRV32 build files, and copy the macro files there. Then, create a Python script which describes the RAM macro in a format which can be imported by SiliconCompiler::

    import siliconcompiler

    def setup(chip):
        # Core values.
        design = 'sky130_sram_2k'
        stackup = chip.get('option', 'stackup')

        # Create library Chip object.
        lib = siliconcompiler.Library(chip, design)
        lib.set('output', stackup, 'gds', f'sram/sky130_sram_2kbyte_1rw1r_32x512_8.gds')
        lib.set('output', stackup, 'lef', f'sram/sky130_sram_2kbyte_1rw1r_32x512_8.lef')
        # Set the 'copy' field to True, to pull these files
        # into the buid directory during the 'import' task.
        lib.set('output', stackup, 'gds', True, field='copy')
        lib.set('output', stackup, 'lef', True, field='copy')

    return lib

You will also need a "blackbox" Verilog file to assure the synthesis tools that the RAM module exists: you can call this file ``sky130_sram_2k.bb.v``. You don't need a full hardware description of the RAM block to generate an ASIC design, but the open-source workflow needs some basic information about the module::

    (* blackbox *)
    module sky130_sram_2kbyte_1rw1r_32x512_8(
    `ifdef USE_POWER_PINS
        vccd1,
        vssd1,
    `endif
    // Port 0: RW
        input clk0,
        input csb0,
        input web0,
        input [3:0] wmask0,
        input [8:0] addr0,
        input [31:0] din0,
        output reg [31:0] dout0,
    // Port 1: R
        input clk1,
        input csb1,
        input [8:0] addr1,
        output reg [31:0] dout1
      );
    endmodule

Next, you need to create a top-level Verilog module containing one ``picorv32`` CPU core, one ``sky130_sram_2k`` memory, and signal wiring to connect their I/O ports together. Note that for the sake of brevity, this module does not include some optional parameters and signals. Check `our picorv32_ram example <https://github.com/siliconcompiler/siliconcompiler/blob/main/examples/picorv32_ram/picorv32_top.v>`_ for a more complete ``picorv32_top`` declaration::

    `timescale 1 ns / 1 ps

    module picorv32_top (
            input clk, resetn,
            output reg trap,

            // Look-Ahead Interface
            output            mem_la_read,
            output            mem_la_write,
            output     [31:0] mem_la_addr,
            output reg [31:0] mem_la_wdata,
            output reg [ 3:0] mem_la_wstrb,

            // Pico Co-Processor Interface (PCPI)
            output reg        pcpi_valid,
            output reg [31:0] pcpi_insn,
            output     [31:0] pcpi_rs1,
            output     [31:0] pcpi_rs2,
            input             pcpi_wr,
            input      [31:0] pcpi_rd,
            input             pcpi_wait,
            input             pcpi_ready,

            // IRQ Interface
            input      [31:0] irq,
            output reg [31:0] eoi,

            // Trace Interface
            output reg        trace_valid,
            output reg [35:0] trace_data
    );

        // Memory signals.
        reg mem_valid, mem_instr, mem_ready;
        reg [31:0] mem_addr;
        reg [31:0] mem_wdata;
        reg [ 3:0] mem_wstrb;
        reg [31:0] mem_rdata;

        // No 'ready' signal in sky130 SRAM macro; presumably it is single-cycle?
        always @(posedge clk)
            mem_ready <= mem_valid;

        // (Signals have the same name as the picorv32 module: use '.*' to autofill)
        picorv32 rv32_soc (
          .*
        );

        // SRAM with always-active chip select and write control bits.
        sky130_sram_2kbyte_1rw1r_32x512_8 sram (
            .clk0(clk),
            .csb0('b0),
            .web0(!(mem_wstrb != 0)),
            .wmask0(mem_wstrb),
            .addr0(mem_addr),
            .din0(mem_wdata),
            .dout0(mem_rdata),
            .clk1(clk),
            .csb1('b1),
            .addr1('b0),
            .dout1()
        );
    endmodule

Finally, your core build script will need to be updated to import the new SRAM Library, and specify some extra parameters such as die size and macro placement::

    import siliconcompiler

    design = 'picorv32_top'
    die_width = 1000
    die_height = 1000

    chip = siliconcompiler.Chip(design)
    chip.load_target('skywater130_demo')

    # Set input source files.
    chip.input(f'{design}.v')
    chip.input('picorv32.v')
    chip.input('sky130_sram_2k.bb.v')
    chip.input('picorv32.sdc')

    # Set die outline and core area.
    chip.set('constraint', 'outline', [(0,0), (die_w, die_h)])
    chip.set('constraint', 'corearea', [(10,10), (die_w-10, die_h-10)])

    # Setup SRAM macro library.
    from sram import sky130_sram_2k
    chip.use(sky130_sram_2k)
    chip.add('asic', 'macrolib', 'sky130_sram_2k')

    # SRAM pins are inside the macro boundary; no routing blockage padding is needed.
    chip.set('tool', 'openroad', 'task', 'route', 'var', 'grt_macro_extension', '0')
    # Disable CDL file generation until we can find a CDL file for the SRAM block.
    chip.set('tool', 'openroad', 'task', 'export', 'var', 'write_cdl', 'false')

    # Place macro instance.
    chip.set('constraint', 'component', 'sram', 'placement', (500.0, 250.0, 0.0))
    chip.set('constraint', 'component', 'sram', 'rotation', 270)

    # Build on a remote server.
    chip.set('option', 'remote', True)
    chip.run()

With all of that done, your top-level build script should take about 15 minutes to run on the cloud servers if they are not too busy. As with the previous designs, you should see periodic updates on its progress, and you should receive a screenshot and metrics summary once the job is complete.

[TODO / CR feedback: Add a screenshot here (or near the top)?]

Extending your design
---------------------

Now that you have a basic understanding of how to assemble modular designs using SiliconCompiler, why not try building a design of your own creation, or adding a custom accelerator to your new CPU core?
