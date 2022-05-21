
<img src="https://raw.githubusercontent.com/siliconcompiler/siliconcompiler/main/docs/_images/sc_logo_with_text.png" alt="drawing" style="height:100px;"/>

[![Quick CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml)
[![Wheels](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml/badge.svg?event=schedule)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml)
[![Documentation Status](https://readthedocs.org/projects/siliconcompiler/badge/?version=latest)](https://docs.siliconcompiler.com/en/latest/?badge=latest)
[![Downloads](https://static.pepy.tech/personalized-badge/siliconcompiler?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/siliconcompiler)

# What is SiliconCompiler?

A modular build system for hardware ("make for silicon"). The project philosophy is to "make the complex possible while keeping the simple simple".

# Why SiliconCompiler?

* Easy to use Python API
* Powerful command line interface
* Standardized JSON schema that supports ASICs, FPGAs, and simulation
* Remote execution (zero install) client/server model
* Cloud scale compilation through flowgraph execution model
* Standardized driver interfaces that simplify adoption of new tools
* Designed to support open and closed proprietary tools
* Built in support for Yosys, OpenRoad, Verilator, Klayout, ([...](https://docs.siliconcompiler.com/en/latest/reference_manual/tools.html))
* Built in support for asap7, freepdk45, skywater130
* Extensive [documentation](https://docs.siliconcompiler.com/en/latest/)

# Supported Technologies

| Type | Supported|
|------|----------|
|**Languages**| C, SV, VHDL, Chisel, Migen/Amaranth, Bluespec
|**Simulation**| Verilator, Icarus, GHDL
| **Synthesis**| Yosys, Vivado, Synopsys, Cadence
| **ASIC APR**| OpenRoad, Synopsys, Cadence
| **FPGA APR**| VPR, nextpnr, Vivado
| **Layout Viewer**| Klayout, Cadence, Synopsys
| **DRC/LVS**| Magic, Mentor, Cadence, Synopsys

# Getting Started

If you already have all of the pre-requisites available, then installation is trivial. Just enter the following from your Python virtual environment:

```sh
pip install --upgrade siliconcompiler
```

It takes less than 10 lines of simple Python code translate RTL into DRC clean GDS.

```python
import siliconcompiler                      # import python package
chip = siliconcompiler.Chip('heartbeat')    # create chip object
chip.load_target('freepdk45_demo')          # load a pre-defined target
chip.set('input', 'verilog', 'heartbeat.v') # set input sources
chip.set('input', 'sdc', 'heartbeat.sdc')   # set constraints
chip.run()                                  # run compilation
chip.summary()                              # print summary
chip.show()                                 # show layout
```

If you prefer working from the command line, you can use the 'sc' app.To get a
complete set of command line switches, enter 'sc -h'.

```sh
sc -input "verilog heartbeat.v" -design heartbeat -target "freepdk45_demo"
```
# Documentation

The full reference manual and tutorials can be found [HERE](https://docs.siliconcompiler.com/en/latest/).

# Installation

SiliconCompiler is available as wheel packages on PyPI for macOS, Windows and
Linux platforms.  If you already have a working Python 3.6-3.10 environment, just use pip.

```sh
python -m pip upgrade siliconcompiler
```

Full complete installation instructions see the
[Installation Guide](https://docs.siliconcompiler.com/en/latest/user_guide/installation.html).

To install the project from source (supported on Linux and macOS platforms):

```bash
git clone https://github.com/siliconcompiler/siliconcompiler
cd siliconcompiler
git submodule update --init --recursive third_party/tools/openroad
pip install -r requirements.txt
python -m pip install -e .
```

# External Tool Dependencies

Installation instructions for all external tools can be found in the
[Tools](https://docs.siliconcompiler.com/en/latest/reference_manual/tools.html) section
of the reference manual. We have included shell setup scripts (Ubuntu) for most of the supported tools. See the [./setup](./setup) directory for a complete set of scripts.

# Contributing

SiliconCompiler is an open-source project and welcomes contributions. To find out
how to contribute to the project, see our
[Contributing Guidelines.](./CONTRIBUTING.md)

## Issues / Bug Reports

We use [GitHub Issues](https://github.com/siliconcompiler/siliconcompiler/issues)
for tracking requests and bugs.

## More information

- **Website:**  https://www.siliconcompiler.com
- **Documentation:**  https://docs.siliconcompiler.com
- **Sources:**  https://github.com/siliconcompiler/siliconcompiler
- **Issues:**  https://github.com/siliconcompiler/siliconcompiler/issues
- **RFCs:**  https://github.com/siliconcompiler/rfcs
- **Discussion:** https://github.com/siliconcompiler/siliconcompiler/discussions

## License

[Apache License 2.0](LICENSE)
