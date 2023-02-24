Building Your Own SoC
=====================

SiliconCompiler supports a "zero-install" remote workflow, which lets you write hardware designs on your local machine and build them on cloud servers. We are currently running a free public beta, and the remote API is a simple collection of HTTP requests which we publish under an open-source license (TODO: link).

You can use the remote flow to try SiliconCompiler or experiment with hardware design, without going through the trouble of building and installing a full suite of open-source EDA tools on your local machine. This tutorial will walk you through the process of building an ASIC containing one PicoRV32 RISC-V CPU core and 2 kilobytes of SRAM, on an open-source 130nm Skywater process node.

Note that our public beta currently only supports open-source tools and PDKs. You can access the public beta without a signup or login, and it is designed to delete your data after your jobs finish, but it is not intended to process proprietary or restricted intellectual property! Please [review our terms of service](TODO), and do not submit IP which you are not allowed to distribute.

You can find complete example designs which reflect the contents of this tutorial in the public SiliconCompiler repository, with RAM and without RAM. (TODO: links)

Installing SiliconCompiler
--------------------------

You must have a recent version of Python v3 and its Pip package manager in order to install SiliconCompiler. We recommend that Windows users download Python from [https://python.org/downloads/](https://www.python.org/downloads/), not the Microsoft Store.

With that, you should be able to install SiliconCompiler directly from PyPi:

`pip install siliconcompiler`

If you are using an older operating system which includes Python v2 as a default, you may need to run:

`pip3 install siliconcompiler`

(TODO: Windows check)

If the installation was successful, you should be able to check which version you have with `sc -version`::

    $ sc -version
    0.9.6

Finally, in order to access the cloud beta, you need to tell SiliconCompiler where your remote server is located. We do not currently require login credentials for our public open-source server, so you can simply run:

`sc-configure https://server.siliconcompiler.com`

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

The job should take a few minutes to run, printing the run's status periodically. After it completes, you should see a table of metrics printed in the command line, and you can find a screenshot of the final GDS-II results at [TODO].

Download PicoRV32 Verilog Code
------------------------------

The heart of any digital design is its HDL code, typically written in a language such as Verilog or VHDL. High-level synthesis languages are gaining in popularity, but most of them still output their final design sources in a traditional HDL such as Verilog.

PicoRV32 is an open-source implementation of a small RISC-V CPU core, the sort you might find in a low-power microcontroller. Its source code, license, and various tooling can be found [in its GitHub repository](https://github.com/YosysHQ/picorv32)

The repository contains many files, but the core CPU design is located in a single file called `picorv32.v` at the root of the repository.

Create a new directory for this project, and copy the `picorv32.v` file into it.

Because we are building this design as an ASIC rather than an FPGA bitstream, you will also need a constraints file to set a reference for the core clock signal. Create a file called `picorv32.sdc` in your new build directory, containing the following line::

    create_clock -name clk -period 10 [get_ports {clk}]

Build the PicoRV32 Core using SiliconCompiler
---------------------------------------------

Before we add the complexity of a RAM macro block, let's build the core design using the open-source Skywater130 PDK. Copy the following build script into the same directory which you copied `picorv32.v` into::

    import siliconcompiler

    chip = siliconcompiler.Chip('picorv32')
    chip.load_target('skywater130_demo')
    chip.input('picorv32.v')
    chip.set('option', 'remote', True)
    chip.run()

If you run that example as a Python script, it should take approximately 10-15 minutes to run if the servers are not too busy. We have not added a RAM macro yet, but this script will build the CPU core with I/O signals placed pseudo-randomly around the edges of the die area. Once the job finishes, you should receive a screenshot of your final design, and a report containing metrics related to the build.

For the full GDS-II results and intermediate build artifacts, you can install the EDA tools on your local system, and run the same Python build script with the `('option', 'remote')` parameter set to `False`. We are not returning the full results during this early beta period because we want to minimize bandwidth, and we believe that the open-source tools/PDKs are currently best suited for rapid prototyping and design exploration.

Adding an SRAM block
--------------------

A CPU core is not very useful without any memory. Indeed, a real system-on-chip would need quite a few supporting IP blocks to be useful in the real world. At the very least, you would want a SPI interface for communicating with external non-volatile memory, a UART to get data in and out of the core, a debugging interface, and a small on-die cache.

In this tutorial, we'll take the first step by adding a small (2 kilobyte) SRAM block and wiring it to the CPU's memory interface. This will teach you how to import and place a hard IP block in your design.

The open-source Skywater130 PDK does not currently include foundry-published memory macros. Instead, they have a set of OpenRAM configurations which are blessed by the maintainers. You can use those configurations (TODO: link) to generate RAM macros from scratch if you are willing to install the OpenRAM utility, or you can download pre-built files which have been published under a permissive license. (TODO: link)

Once you have a GDS and LEF file for your RAM macro, create a new directory called `sram` in same location as your PicoRV32 build files, and copy the macro files there. Then, create a Python script which describes the RAM macro in a format which can be imported by SiliconCompiler::

    import siliconcompiler
    # TODO

Next, your core build script will need to be updated to import the new SRAM Library, and specify some extra parameters such as die size and macro placement::

    # TODO

Finally, you will need to modify the PicoRV32 Verilog source code to instantiate the RAM block and connect it the CPU's memory interface::

    # TODO

With all of that done, your top-level build script should take about 15 minutes to run on the cloud servers if they are not too busy. As with the previous designs, you should see periodic updates on its progress, and you should receive a screenshot and metrics summary once the job is complete.

Extending your design
---------------------

Now that you have a basic understanding of how to assemble modular designs using SiliconCompiler, why not try building a design of your own creation, or adding a custom accelerator to your new CPU core?
