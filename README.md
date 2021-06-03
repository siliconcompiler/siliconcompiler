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

To build the GCD example circuit using SiliconCompiler, run:
```bash
>> ./examples/gcd/run.sh
```

This will produce a GDSII output at `build/gcd/job1/export/outputs/gcd.gds`,
which can then be viewed in KLayout.
