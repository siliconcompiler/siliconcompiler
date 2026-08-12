![SiliconCompiler](https://raw.githubusercontent.com/siliconcompiler/siliconcompiler/main/docs/_static/sc_logo_with_text.png)

[![Python CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/python_ci.yml/badge.svg?branch=main)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/python_ci.yml)
[![Tools CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/tools_ci.yml/badge.svg?branch=main)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/tools_ci.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_ci.yml/badge.svg?branch=main)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_ci.yml)
[![Wheels](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml/badge.svg?branch=main)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml)
[![Lint](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/lint.yml)
[![Documentation Status](https://readthedocs.org/projects/siliconcompiler/badge/?version=latest)](https://docs.siliconcompiler.com/en/latest/?badge=latest)
[![codecov](https://codecov.io/github/siliconcompiler/siliconcompiler/branch/main/graph/badge.svg?token=V5BQR42Q8C)](https://codecov.io/github/siliconcompiler/siliconcompiler)
[![Downloads](https://static.pepy.tech/personalized-badge/siliconcompiler?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/siliconcompiler)

# Introduction

SiliconCompiler is a modular hardware build system ("make for silicon"). The project philosophy is to "make the complex possible while keeping the simple simple".

# Supported Technologies

| Type | Supported|
|------|----------|
|**Design Languages**| C, Verilog, SV, VHDL, Chisel, Migen/Amaranth, Bluespec, [MLIR](https://en.wikipedia.org/wiki/MLIR_(software))
|**Simulation Tools**| Verilator, Icarus, GHDL, Xyce
|**Synthesis**| Yosys, Vivado, Synopsys, Cadence
|**ASIC APR**| OpenROAD, Synopsys, Cadence
|**FPGA APR**| VPR, nextpnr, Vivado
|**Layout Viewer**| Klayout, OpenROAD, Cadence, Synopsys
|**DRC/LVS**| Klayout, Magic, Synopsys, Siemens
|**Open PDKs**| sky130, ihp130, gf180, asap7, freepdk45, gt2n, interposer — all shipped by [lambdapdk](https://github.com/siliconcompiler/lambdapdk)
|**Foundry PDKs**| gf12lp, gf22fdx, intel16 — require a foundry agreement; package them yourself following the [external library guide](https://docs.siliconcompiler.com/en/latest/development_guide/external_libraries.html)

# Getting Started

SiliconCompiler is available as wheel packages on PyPI for macOS, Windows and
Linux platforms. For working Python 3.10-3.14 environment, just use pip.
On Windows, use remote or Docker execution — local tool flows are supported on Linux and macOS.

```sh
pip install --upgrade siliconcompiler
```

Converting RTL into DRC clean GDS takes 13 lines of simple Python code.
(`asicflow` reports geometric violations from detailed routing as the `drcs` metric, and electrical ones — slew, capacitance, fanout, antenna — as `drvs`. Signoff DRC and LVS run in the separate `signoffflow`.)

```python
from siliconcompiler import ASIC, Design               # import python package
from siliconcompiler.targets import skywater130_demo
design = Design("heartbeat")                           # create design object
design.set_topmodule("heartbeat", fileset="rtl")       # set top module
design.add_file("heartbeat.v", fileset="rtl")          # add input sources
design.add_file("heartbeat.sdc", fileset="sdc")        # add input sources
project = ASIC(design)                                 # create project
project.add_fileset(["rtl", "sdc"])                    # enable filesets
skywater130_demo(project)                              # load a pre-defined target
project.option.set_remote(True)                        # enable remote execution
project.run()                                          # run compilation
project.summary()                                      # print summary
project.show()                                         # show layout
```

> [!NOTE]
> The required files can be found at: [heartbeat example](https://github.com/siliconcompiler/siliconcompiler/tree/main/examples/heartbeat)

# Not building an ASIC?

The example above is an ASIC build, but the same `Design` feeds every flow. The
project class is what decides what happens to it:

| Goal | Class | Tools needed | Start here |
|------|-------|--------------|------------|
| Lint your RTL | `Lint` | none | [Lint your RTL](https://docs.siliconcompiler.com/en/latest/user_guide/tutorials/lint.html) |
| Simulate, or prove properties formally | `Sim` | Verilator, Icarus, GHDL or SymbiYosys | [Simulate and verify](https://docs.siliconcompiler.com/en/latest/user_guide/tutorials/simulate.html) |
| Build an FPGA bitstream | `FPGA` | Yosys, plus VPR or nextpnr | [Build for an FPGA](https://docs.siliconcompiler.com/en/latest/user_guide/tutorials/fpga.html) |

Linting is the quickest way to see SiliconCompiler work: the default linter ships
as a Python package, so it needs no EDA tools installed at all. For a complete
FPGA build with nothing installed locally, the demo runs remotely:

```sh
python3 -m siliconcompiler.demos.fpga_demo -remote
```

# Why SiliconCompiler?

* **Ease-of-use**: Programmable with a simple [Python API](https://docs.siliconcompiler.com/en/latest/reference_manual/schema_api.html)
* **Portability:** Powerful dynamic JSON [schema](https://docs.siliconcompiler.com/en/latest/reference_manual/schema.html) supports ASIC and FPGA design and simulation
* **Speed:** Flowgraph [execution model](https://docs.siliconcompiler.com/en/latest/user_guide/execution_model.html) enables cloud scale execution.
* **Friction-less:** [Remote execution model](https://docs.siliconcompiler.com/en/latest/development_guide/remote_processing.html) enables "zero install" compilation
* **Modularity:** [Tool abstraction layer](https://docs.siliconcompiler.com/en/latest/development_guide/tools.html) makes it easy to add/port new tools to the project.
* **Provenance:** [Compilation manifests](https://docs.siliconcompiler.com/en/latest/user_guide/data_model.html) created automatically during execution.
* **Documented:** An extensive set of auto-generated high quality [reference documents](https://docs.siliconcompiler.com/).
* **In-use:** Actively used by Zero ASIC for commercial tapeouts at advanced process nodes.

# Documentation

New here? Start with the [Quickstart guide](https://docs.siliconcompiler.com/en/latest/user_guide/quickstart.html), which walks through the example above line by line.

The [SiliconCompiler reference manual and tutorials](https://docs.siliconcompiler.com/) cover the rest.

# License

[Apache License 2.0](https://github.com/siliconcompiler/siliconcompiler/blob/main/LICENSE)

# How to Cite

If you want to cite our work, please use the following paper:

A. Olofsson, W. Ransohoff, N. Moroze, "[Invited: A Distributed Approach to Silicon Compilation](https://github.com/siliconcompiler/siliconcompiler/blob/main/docs/papers/sc_dac2022.pdf)", 59th Design Automation Conference (DAC), 10-14 July 2022, San Francisco, CA, USA. Published, 7/2022.

Bibtex:
```
@inproceedings{10.1145/3489517.3530673,
  author = {Olofsson, Andreas and Ransohoff, William and Moroze, Noah},
  title = {A Distributed Approach to Silicon Compilation: Invited},
  year = {2022},
  booktitle = {Proceedings of the 59th ACM/IEEE Design Automation Conference},
  pages = {1343–1346},
  location = {San Francisco, California}
}
```

# Installation

Complete installation instructions are available in the [Installation Guide](https://docs.siliconcompiler.com/en/latest/user_guide/installation.html).

To install the project from source (recommended for developers only).

```bash
git clone https://github.com/siliconcompiler/siliconcompiler
cd siliconcompiler
python3 -m venv .venv        # Setup virtual environment
source .venv/bin/activate
pip install --upgrade pip    # Update pip
pip install -e .             # Required install step
pip install -e .[test,lint]  # Optional install step for running tests and lint
pip install -e .[docs]       # Optional install step for generating docs
```

# EDA Tool Installation

Installation instructions for all external tools can be found in the
[External Tools](https://docs.siliconcompiler.com/en/latest/user_guide/installation.html#external-tools) section
of the user guide. We have included shell setup scripts (Ubuntu) for most of the supported tools, which can be accessed via [sc-install](https://docs.siliconcompiler.com/en/latest/reference_manual/apps.html#app-sc-install).
See the [siliconcompiler/toolscripts](https://github.com/siliconcompiler/siliconcompiler/tree/main/siliconcompiler/toolscripts) directory for a complete set of scripts and [siliconcompiler/toolscripts/_tools.json](https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/toolscripts/_tools.json) for the currently recommended tool versions.

# Contributing

SiliconCompiler is an open-source project and welcomes contributions. To find out
how to contribute to the project, see our
[Contributing Guidelines](https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md).

# Getting help

**[Discussions](https://github.com/siliconcompiler/siliconcompiler/discussions)
is the best place to ask a question.** The
[Help (Q&A)](https://github.com/siliconcompiler/siliconcompiler/discussions/categories/help-q-a)
category is actively answered and is worth searching before you post — the answer
to "how do I harden a macro", "how are filesets ordered" or "why won't this PDK
build" is often already there.

Also useful:

- [Frequently asked questions](https://docs.siliconcompiler.com/en/latest/user_guide/faq.html)
- [How do I…?](https://docs.siliconcompiler.com/en/latest/user_guide/howto.html) — a task-oriented reference
- [Glossary](https://docs.siliconcompiler.com/en/latest/user_guide/glossary.html)

We use [GitHub Issues](https://github.com/siliconcompiler/siliconcompiler/issues)
for tracking requests and bugs. If you hit a tool failure,
[`sc-issue`](https://docs.siliconcompiler.com/en/latest/reference_manual/apps.html#app-sc-issue)
packages a runnable test case to attach.

# More information

| Resources | Link|
|-----------|-----|
| **Website**|  https://www.siliconcompiler.com |
| **Documentation**|  https://docs.siliconcompiler.com |
| **Discussions**| https://github.com/siliconcompiler/siliconcompiler/discussions |
| **Sources**|  https://github.com/siliconcompiler/siliconcompiler |
| **Issues**|  https://github.com/siliconcompiler/siliconcompiler/issues |
| **Open PDKs**| https://github.com/siliconcompiler/lambdapdk — every open PDK and standard cell library SiliconCompiler ships |
| **Portable RTL libraries**| https://github.com/siliconcompiler/lambdalib — technology-independent blocks, including the pad ring |
