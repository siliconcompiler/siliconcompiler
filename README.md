# Silicon Compiler Collection (SCC)

![CI Tests](https://github.com/zeroasiccorp/siliconcompiler/workflows/CI%20Tests/badge.svg)

## Introduction

* schema.py defines the silicon compiler architecture
* core.py defines the python user API for accessing the schema
* setup.py defines a set of pre-configured targets for FPGAs and ASICs
* cli.py is the command line silicon compiler

## Pre-Requisites

* verilator: front end parsing
* yosys:     synthesis
* openroad:  netlist to GDSII
* klayout :  general gui, file conversion

Python3 libraries (`pip3 install -r requirements.txt`):
* numpy:      linear algebra
* matploblib: graphing / SVG processing
* ply:        generic lexer / parser


## Local Installation
Python installation will depend on your environment. The example below is based on running python3 and pipenv

```
git clone https://github.com/zeroasiccorp/siliconcompiler
cd siliconcompiler
python3 -m pip install -e .

```

## Examples

Below you can see a number of simple exaples and use cases that hopefully illustrate the power and simplicity of SCC. For a complete set of variables and command line switches, see the Arguments section of the README file.


#### *Hello world*
* The example synthesizes, places, and routes a design using a default process design kit (ASAP7) and standard cell library.
* A square floor-plan is auto-generated for the design.
* No timing constraints are provided
* Outputs:  build/hello.vg (netlist), build/hello.gds, build/hello.def

```bash
>> echo "module hello(input a, input b, output c); assign c = a & b; endmodule " > hello.v
>> sc hello.v
>> klayout hello.gds
```

#### *Synchronous Design*
* This example uses the [-clk] switch to defines the "clk" signal as a clock and constraints it to a 1 ns minimum cycle time
* Outputs:  build/hello.vg (netlist), build/hello.gds

```bash
>> echo "module hello(input a, input b, input clk, output reg c); always @ (posedge clk) c <= a & b; endmodule " > hello.v
>> sc -clk "clk 1ns" hello.v
```

#### *With SDC iming Constraints*
* For modules with complex timing constraints, timing constraints are generally specifie using the Synopsys Design Constraints (SDC) format.
* This example shows an example synthesized using a full set of SDC constraints.

```bash
>> sc -constraints examples/hello_world/hello_world.sdc examples/hello_world/hello_world.v
```

#### *Specifying Compilation Target*
* This example shows how to specify a target process and standard cell libraries used for compilation.

```bash
>> sc -foundry "skywater" -process "130nm" -library "openlib" -sdc examples/oh/common/sdc/default.sdc -y examples/oh/common examples/oh/common/hdl/oh_fifo_sync.v
```

#### *Floorplan*
* This example shows how to input a floorplan file in specified in the industry standard Design Exchange Format (DEF).
* The DEF file can be generated from source code of from a graphical floor-planning tool.  

```bash
>> sc -clk "clk 1ns"  -def examples/oh/common/floorplan/oh_fifo_sync.def examples/oh/common/hdl/oh_fifo_sync.v
```

#### *FPGA Compilation*
* This example shows how to compile for an FPGA
* The device should match the device name used for the FPGA tool-chain

```bash
>> sc -mode fpga -flow "vivado" -device "zynq" examples/oh/common/sdc/default.sdc -y examples/oh/common examples/oh/common/hdl/oh_fifo_sync.v
```



#### *Generating a JSON configuration file*
* Configurations are created in Python using the siliconcompuler package API
* The configuration is then saved in a json file  

```bash
>> python3 examples/generate_json/generate_json.py
```


#### *Using File Based Configuration*
* For complex projects, it may be more efficient to drive all command arguments from a configuration file.
* This example shows how scc can be configured from a "json" configuration file, incorporating all of the previous switches in one file.  

```bash
>> sc -cfg examples/hello_world/hello_world.json examples/hello_world/hello_world.v
```

#### *Hierarchical Design*
* This example demonstrates compilation of a hierarchical design with sub-modules spread out over multiple directories
* The [ -y ] switch defines a module search search directory (same behavior as Icarus and Verilator)

```bash
>> sc -clk "clk 1ns" -y examples/oh/common examples/oh/common/oh_fifo_sync.v
```

#### *Parametrized Design*
* Many designs are parametrized to maximize reuse. This example shows two valid methods for setting parameters at compile time.
* The first example demonstrates setting parameters through a file
* The second example shows how parameters can be overriden at the command line

```bash
>>> echo "define CFG_DW 32" > define.vh
>>> echo "module   hello #(parameter DW = CFG_DW) (input a[DW-1:0], input b[DW-1:0], input clk, output reg c[DW-1:0]); always @ (posedge clk) c <= a & b; endmodule " > hello.v

>> sc -clk "clk 1ns" define.vh hello.v
>> sc -clk "clk 1ns" -DCFG_DW=32 hello.v
```


#### *Display All Configuration Parameters*
* The scc is imminently configurable allowing for setting variables through command line switches (highet), json config file, environment variables, and built-in default (lowest).
* This example prints out an alphabetized list of settings of all compiler Variaables

```bash
>> scc -printcfg
```



