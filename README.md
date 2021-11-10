
![alt text](docs/_images/sc_logo_with_text.png)

[![Quick CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml)
[![Documentation](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml)
[![Wheels](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml/badge.svg?event=schedule)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml)

SiliconCompiler ("SC") is a open source compiler infrastructure project that aims
to lower the barrier to hardware specialization through a simple distributed
programming model and standardized tool configurations.

- **Website:**  https://www.siliconcompiler.com
- **Documentation:**  https://www.siliconcompiler.com/docs
- **Sources:**  https://github.com/siliconcompiler/siliconcompiler
- **Issues:**  https://github.com/siliconcompiler/siliconcompiler/Issues
- **RFCs:**  https://github.com/siliconcompiler/rfcs
- **Disussion:** https://github.com/siliconcompiler/siliconcompiler/discussions

## Quick Start

Hardware compilation includes four basic steps:

 1. Create a SiliconCompiler instance.
 2. Set up all compilation parameters.
 3. Run compilation.
 4. Inspect results.

For simple prepackaged flows, only a small number of parameters need to be set.
The following Python code snippet illustrates the basics. For a complete set of
parameters, functions, and examples
[READ THE DOCS](https://www.siliconcompiler.com/docs).

```python
import siliconcompiler                        # import python package
chip = siliconcompiler.Chip()                 # create chip object
chip.set('source', 'heartbeat.v')             # define list of sources
chip.set('design', 'heartbeat')               # set top module name
chip.clock(name='clk', pin='clk', period=1.0) # define a clock
chip.target('asicflow_freepdk45')             # load pre-defined flow
chip.run()                                    # run compilation
chip.summary()                                # print run summary
chip.show()                                   # show layout
```

## Installation

SiliconCompiler is available as wheel packages for macOS, Windows and Linux on
PyPI. To install the current release in your Python environment:

```sh
  python -m pip install siliconcompiler
```

Installation is also supported from source on Linux and macOS platforms:

```bash
 git clone https://github.com/siliconcompiler/siliconcompiler
 cd siliconcompiler
 pip install -r requirements.txt
 python -m pip install -e .
```

## Dependancies

All SiliconCompiler based compilation flows depend on the correct operation of
external executables. Installation instructions for all supported tools can be
found in the tools directory of the
[documentation](https://www.siliconcompiler.com/docs).

## Contributing

To find out how to contribute to the project, please see our
[contributing guidelines](./CONTRIBUTING.md)

## Issues / Bug Reports

We use [GitHub issues](https://github.com/siliconcompiler/siliconcompiler/Issues)
for tracking requests and bugs.


## Licensing
