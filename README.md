# SiliconCompiler

[![Quick CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml)

SiliconCompiler is an end-to-end Python based open source platform for hardware compilation. It supports a comprehensive, flexible ecosystem of [tools](https://www.siliconcompiler.org/tools), [hardware targets](https://www.siliconcompiler.org/targets), and [community](https://www.siliconcompiler.org/community) resources that lowers the barrier to physical ASIC prototyping and high accuracy HW/SW codesign.

**Highlights:**
* Configurable, extensible, and automated ASIC and FPGA compilation flows
* Compilation configuration dictionary with over 200 parameters
* Command line application with full configuration access
* Plain text single file JSON compilation record
* Zero install client/server execution model
* Simple name based target technology mapping
* Python based technology agnostic ASIC floor-planning API

**App Example:**

```sh
$ sc hello_world.v -target asap7
```

**Python Example:**
```python
import siliconcompiler
chip = siliconcompiler.Chip()
chip.add('source', 'hello.v')
chip.target('asap7')
chip.run()
```

## Documentation

We take documentation serisouly and have crated detailed documentation of the architecture, options, configuration, Python API.

Please spend a few minutes to review the docs before diving in:

https://www.siliconcompiler.com/docs


## Installation

To install the current release from PyPI.
```sh
$ pip install siliconcompiler
```

To install from the active developer repository.

```sh
$ git clone https://github.com/siliconcompiler/siliconcompiler
$ cd siliconcompiler
$ git submodule update --init --recursive third_party/tools/openroad
$ pip install -r requirements.txt
$ python -m pip install -e .
```

Note that this installation process will build a C++ LEF parser from source,
using code contained in one of SC's submodules. In order to build this parser,
you must install bison:
```sh
$ sudo apt-get install bison
```

All other build prerequisites should be installed transparently by Pip.

## Pre-requisites

To compile designs using the included open source target flow, you will need to install the follwoing external packages:

Ubuntu based install scripts can be found in the [./setup](setup) directory. These scripts will install dependencies into `siliconcompiler/deps`, and usually build them from source.

- **OpenRoad:** https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts
  - Following the directions in the OpenROAD-flow-scripts repository will
    install other required dependencies, such as [Yosys](https://github.com/YosysHQ/yosys),
    along with OpenROAD itself. This repository is added as a git submodule under `third_party/tools`.
    We recommend installing from this submodule, since the OpenROAD API is unstable and this
    version is known compatible with SiliconCompiler.
- **Verilator:** https://github.com/verilator/verilator
- **Klayout:** https://github.com/KLayout/klayout
  -  Requires version >=0.26.11.
- **Surelog:** https://github.com/chipsalliance/Surelog
- **sv2v:** https://github.com/zachjs/sv2v

To run the FPGA flows, the following additional dependencies are required:
- **NextPNR-ice40:** https://github.com/YosysHQ/nextpnr
- **Icestorm tools:** https://github.com/YosysHQ/icestorm
- **OpenFPGA:** https://github.com/lnis-uofu/OpenFPGA

If you have Vagrant and VirtualBox installed, you can select the tools that you want to be automatically installed by modifying the `Vagrantfile`. Then run `vagrant up` to initialize the VM (this will take a while the first time when everything installs), and `vagrant ssh` to connect to the VM.

SiliconCompiler have also been tested with commercial EDA tools and PDKs, but these configurations cannot be disclosed due to IP restrictions.

## Testing Installation

```bash
$ sc examples/gcd/gcd.v -design gcd -target freepdk45_asic -constraint examples/gcd/gcd.sdc
$ sc build/gcd/job1/export/outputs/gcd.gds -display
```

## Contributing
If you want to contribute to SiliconCompiler, be sure to review the [contributing guidelines](./CONTRIBUTING.md)
We use GitHub issues for tracking requests and bugs.

## Other Resources

- **Website:** https://siliconcompiler.com
- **Community:** https://siliconcompiler.com/community

## Similar projects

* [Edalize](https://github.com/olofk/edalize) - Edalize is a Python Library for interacting with EDA tools
* [OpenLane](https://github.com/The-OpenROAD-Project/OpenLane) - OpenLANE is an automated RTL to GDSII flow
* [SymbiFlow](https://github.com/SymbiFlow) - Open source flow for generating bitstreams from Verilog
