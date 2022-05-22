![SiliconCompiler](https://raw.githubusercontent.com/siliconcompiler/siliconcompiler/main/docs/_images/sc_logo_with_text.png)

[![Quick CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml)
[![Wheels](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml/badge.svg?event=schedule)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml)
[![Documentation Status](https://readthedocs.org/projects/siliconcompiler/badge/?version=latest)](https://docs.siliconcompiler.com/en/latest/?badge=latest)
[![Downloads](https://static.pepy.tech/personalized-badge/siliconcompiler?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/siliconcompiler)

# What is SiliconCompiler?

A modular build system for hardware ("make for silicon"). The project philosophy is to "make the complex possible while keeping the simple simple".

# Why SiliconCompiler?

* Easy to use [Python API](https://docs.siliconcompiler.com/en/latest/user_guide/programming_model.html)
* Standard JSON [schema](https://docs.siliconcompiler.com/en/latest/reference_manual/schema.html) with support for ASICs, FPGAs, and simulation
* Flowgraph [compilation model](https://docs.siliconcompiler.com/en/latest/user_guide/execution_model.html) that leverages cloud scale compute farms     
* Client/server [remote execution](https://docs.siliconcompiler.com/en/latest/user_guide/remote_processing.html) support ("zero install")
* Tool [driver interface](architecture) that enables support open and proprietary tool
* Automated creation of [design manifest](https://docs.siliconcompiler.com/en/latest/user_guide/data_model.html) for reuse/provenance
* Extensively [documentated](https://docs.siliconcompiler.com/en/latest/)
* Used by the Zero ASIC design teams for commercial tapouts

# Supported Technologies

| Type | Supported|
|------|----------|
|**Languages**| C, SV, VHDL, Chisel, Migen/Amaranth, Bluespec
|**Simulation**| Verilator, Icarus, GHDL
|**Synthesis**| Yosys, Vivado, Synopsys, Cadence
|**ASIC APR**| OpenRoad, Synopsys, Cadence
|**FPGA APR**| VPR, nextpnr, Vivado
|**Layout Viewer**| Klayout, Cadence, Synopsys
|**DRC/LVS**| Magic, Mentor, Cadence, Synopsys
|**PDKs**| sky130, asap7, freepdk45

# Getting Started

SiliconCompiler is available as wheel packages on PyPI for macOS, Windows and
Linux platforms. For working Python 3.6-3.10 environment, just use pip.

```sh
python -m pip upgrade siliconcompiler
```


Converting RTL into DRC clean GDS takes less than 10 lines of simple Python code.

```python
import siliconcompiler                      # import python package
chip = siliconcompiler.Chip('heartbeat')    # create chip object
chip.load_target('freepdk45_demo')          # load a pre-defined target
chip.set('input', 'verilog', 'heartbeat.v') # set input sources
chip.set('input', 'sdc', 'heartbeat.sdc')   # set constraints
#chip.set('option','remote', True)          # enable remote execution
chip.run()                                  # run compilation
chip.summary()                              # print summary
chip.show()                                 # show layout
```

To reduce the pain of tool installation, the project supports remote compilation on [siliconcompiler.com](): 
1. Sign up for a [Free Beta Account](https://www.siliconcompiler.com/beta),
2. Create a [credentials file](https://docs.siliconcompiler.com/en/latest/user_guide/installation.html#cloud-access)
3. Set the remote option to True (see example above)
4. Run   

Simple designs can be compiled using the built in command line 'sc' app:

```sh
sc -remote -input "verilog heartbeat.v" -design heartbeat -target "freepdk45_demo"
```

# Documentation

The full reference manual and tutorials can be found [HERE](https://docs.siliconcompiler.com/en/latest/).

# Installation


Complete installation instructions are available in the [Installation Guide](https://docs.siliconcompiler.com/en/latest/user_guide/installation.html).

To install the project from source (recommended for developers only).

```bash
git clone https://github.com/siliconcompiler/siliconcompiler
cd siliconcompiler
git submodule update --init --recursive third_party/tools/openroad
pip install -r requirements.txt
python -m pip install -e .
```

# Tool Installation

Installation instructions for all external tools can be found in the
[Tools](https://docs.siliconcompiler.com/en/latest/reference_manual/tools.html) section
of the reference manual. We have included shell setup scripts (Ubuntu) for most of the supported tools. See the [./setup](./setup) directory for a complete set of scripts.

# Contributing

SiliconCompiler is an open-source project and welcomes contributions. To find out
how to contribute to the project, see our
[Contributing Guidelines.](./CONTRIBUTING.md)

# Issues / Bug Reports

We use [GitHub Issues](https://github.com/siliconcompiler/siliconcompiler/issues)
for tracking requests and bugs.

# License

[Apache License 2.0](LICENSE)

# More information

| Resources | Link|
|-----------|-----|
| **Website**|  https://www.siliconcompiler.com
| **Documentation**|  https://docs.siliconcompiler.com
| **Sources**|  https://github.com/siliconcompiler/siliconcompiler
| **Issues**|  https://github.com/siliconcompiler/siliconcompiler/issues
| **RFCs**|  https://github.com/siliconcompiler/rfcs
| **Discussion**| https://github.com/siliconcompiler/siliconcompiler/discussions
