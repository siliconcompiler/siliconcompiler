
![alt text](docs/_images/sc_logo_with_text.png)

[![Quick CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml)
[![Documentation](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml)
[![Wheels](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml/badge.svg?event=schedule)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml)


- **Website:**  https://www.siliconcompiler.com
- **Documentation:**  https://docs.siliconcompiler.com
- **Sources:**  https://github.com/siliconcompiler/siliconcompiler
- **Issues:**  https://github.com/siliconcompiler/siliconcompiler/issues
- **RFCs:**  https://github.com/siliconcompiler/rfcs
- **Discussion:** https://github.com/siliconcompiler/siliconcompiler/discussions


## Mission

SiliconCompiler is an open source compiler framework that aims to automate
translation from source code to silicon.

## Project Overview

The SiliconCompiler project includes a standardized compiler data Schema, a Python
object oriented API, and a distributed systems execution model. The project
philosophy is to "make the complex possible while keeping the simple simple".

Intrigued? Check out the extensive [documentation!](https://docs.siliconcompiler.com)


```python
import siliconcompiler                    # import python package
chip = siliconcompiler.Chip()             # create chip object
chip.target('asicflow_freepdk45')         # load pre-defined flow
chip.set('source', 'heartbeat.v')         # define list of sources
chip.set('design', 'heartbeat')           # set top module name
chip.set('constraint', 'heartbeat.sdc')   # define constraints
chip.set('remote', True)                  # compiler remotely
chip.run()                                # run compilation
chip.summary()                            # print run summary
chip.show()                               # show layout
```

## Command Line Interface

Command line interface programs are very effective for quick experimentation.
SiliconCompiler includes a command line program 'sc',  with full support for all
compiler schema parameters. For simple designs, compiling using *sc* is as
easy as using gcc or llvm.

```bash
pip install siliconcompiler
echo "module flipflop (input clk, d, output reg out); \
	always @ (posedge clk) out <= d; endmodule"> flipflop.v
sc flipflop.v -remote
```
More complex designs are handled by simply adding more options.

```bash
sc hello.v add.v -remote -constraint hello.sdc -target "asicflow_skywater130"
```

## Installation

SiliconCompiler is available as wheel packages on PyPI for macOS, Windows and
Linux platforms. Full complete installation instructions see the
[Installation Guide](https://docs.siliconcompiler.com/en/latest/user_guide/installation.html).
If you already have a working Python 3.6-3.10 environment, just use pip:

```sh
python -m pip install siliconcompiler
```

To install the project from source (supported on Linux and macOS platforms):

```bash
git clone https://github.com/siliconcompiler/siliconcompiler
cd siliconcompiler
git submodule update --init --recursive third_party/tools/openroad
pip install -r requirements.txt
python -m pip install -e .
```

## External Dependencies

Installation instructions for all external tools can be found in the
[Tools Directory](https://docs.siliconcompiler.com/en/latest/reference_manual/tools.html).
For the '-remote' option, there are no external dependencies.

## Contributing

SiliconCompiler is an open-source project and welcomes contributions. To find out
how to contribute to the project, see our
[Contributing Guidelines.](./CONTRIBUTING.md)

## Issues / Bug Reports

We use [GitHub Issues](https://github.com/siliconcompiler/siliconcompiler/issues)
for tracking requests and bugs.

## License

[Apache License 2.0](LICENSE)
