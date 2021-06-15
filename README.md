# SiliconCompiler

![CI Tests](https://github.com/zeroasiccorp/siliconcompiler/workflows/CI%20Tests/badge.svg)

SiliconCompiler is an end-to-end open source platform for hardware compilation. It supports a comprehensive, flexible ecosystem of [tools](https://www.siliconcompiler.org/tools), [hardware targets](https://www.siliconcompiler.org/targets), and [community](https://www.siliconcompiler.org/community) resources that lowers the barrier for virtual architecture prototyping and physical implementation. 

SiliconComiler provides a stable JSON configuration schema, command line interface, and Python API with over 200 configuration parameters and 25 core functions.

## Documentation

One of the goals of the SiliconCompiler project is to reduce the information access barrier for aspiring hardware designers. So far we have created over 100 pages of detailed documentation of the architecture, options, configuration, Python API. 

In addition, we have created a number of tutorials and examples that reflect recommended design practices. 

We hope you will spend a few minutes to review the docs before diving in. 

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
$ pip install -r requirements.txt
$ python -m pip install -e .
```

## Pre-requisites

The SiliconCompiler project supports open source as well as commercial EDA flows. The open source reference flow included in the project depends on the external packages listed below: 

- **OpenRoad:** https://github.com/The-OpenROAD-Project/OpenROAD
- **OpenSTA:** https://github.com/The-OpenROAD-Project/OpenSTA
- **ABC**: https://github.com/berkeley-abc/abc
- **Yosys:** https://github.com/YosysHQ/yosys
- **Verilator:** https://github.com/verilator/verilator
- **Klayout:** https://github.com/KLayout/klayout
- **VTR:** https://github.com/verilog-to-routing/vtr-verilog-to-routing

Ubuntu based install scripts can be found in the [./setup](setup) directory.

## Testing installation

```bash
$ sc examples/gcd/gcd.v -design gcd -target freepdk45_asic -constraint examples/gcd/gcd.sdc
$ sc build/gcd/job1/export/outputs/gcd.gds -display
```

## Write your first SiliconCompiler program

```sh
$ python
```

```python
>>> import siliconcompiler
>>> chip = siliconcompiler.Chip()
>>> chip.add('source', 'examples/gcd/gcd.v')
>>> chip.add('constraint', 'examples/gcd/gcd.sdc')
>>> chip.set('design', 'gcd')
>>> chip.set('target', 'freepdk45')
>>> chip.target()
>>> chip.run()
>>> chip.summary()
>>> chip.display()
```

## Contributing
If you want to contribute to SiliconCompiler, be sure to review the [contributing guidelines](./CONTRIBUTING.md)
We use GitHub issues for tracking requests and bugs.

## Other Resources

- **Website:** https://www.siliconcompiler.com
- **Community:** https://www.siliconcompiler.com/community

## Similar projects

* [Edalize](https://github.com/olofk/edalize) - Edalize is a Python Library for interacting with EDA tools
* [OpenLane](https://github.com/The-OpenROAD-Project/OpenLane) - OpenLANE is an automated RTL to GDSII flow
* [SymbiFlow](https://github.com/SymbiFlow) - Open source flow for generating bitstreams from Verilog
