
![alt text](docs/_images/sc_logo_with_text.png)

[![Quick CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml)
[![Documentation](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml)
[![Wheels](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml/badge.svg?event=schedule)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml)

SiliconCompiler is an open source compiler framework that aims to enable automated translation from source code to silicon.

- **Website:**  https://www.siliconcompiler.com
- **Documentation:**  https://docs.siliconcompiler.com
- **Sources:**  https://github.com/siliconcompiler/siliconcompiler
- **Issues:**  https://github.com/siliconcompiler/siliconcompiler/issues
- **RFCs:**  https://github.com/siliconcompiler/rfcs
- **Disussion:** https://github.com/siliconcompiler/siliconcompiler/discussions

## Command Line Interface

SiliconCompiler supports a simple command line interface 'sc' and an advanced
Python API. Both models offer full access to 300+ standardized compiler
schema parameters. For a complete set of parameters, functions, and examples
read the [DOCUMENTATION](https://docs.siliconcompiler.com)!



#### Hello world
For very simple designs, compiling using *sc* is as easy as using gcc or llvm.

```bash
pip install siliconcompiler
sc hello.v
```

#### Remote Compilation

To simplify tool installation and job scheduling, SiliconCompiler supports a
"-remote" option, which directs the compiler to send all steps to a remote
server for processing. The -remote option relies on a credentials file located at
~/.sc/credentials on Linux or macOS, or at C:\Users\USERNAME\\.sc\credentials on Windows.

```bash
sc hello.v -remote
```

#### Complex design
More complex designs are handled by adding  more  options. For
scenarios with more than five command line options, the SiliconCompiler
Python interface is usually a better option.

```bash
sc hello.v add.v -constraint hello.sdc -target "asicflow_skywater130"
```


## Python Interface
The SiliconCompiler
[PYTHON API]((https://docs.siliconcompiler.com/reference_manual/schema.html) is
a abstraction layer that sits on top of the compilation configuration
[SCHEMA](https://docs.siliconcompiler.com/reference_manual/schema.html). The Python interface enables sophisticated design compilations that leverage the
full power of the Python programming language and package platform.

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

SiliconCompiler is available as wheel packages on PyPI for macOS, Windows and
Linux platforms. Full installation instructions can be found in the [USER GUIDE](https://docs.siliconcompiler.com/user_guide/installation.html) If you
already have a working Python 3.6-3.10 environment, installation is simply:

```sh
python -m pip install siliconcompiler
```
To install the project from source (supported on Linux and macOS platforms):

```bash
git clone https://github.com/siliconcompiler/siliconcompiler
cd siliconcompiler
pip install -r requirements.txt
python -m pip install -e .
```

## External Dependencies

SiliconCompiler depends on the correct installation of external executables to
run locally. Installation instructions for all external tools can be found in the [TOOLS](https://docs.siliconcompiler.com/reference_manual/tools.html) documentation. For the '-remote' option,
there are no external dependencies.   

## Contributing

We need help! To find out how to contribute to the project, see our
[CONTRIBUTING GUIDELINES.](./CONTRIBUTING.md)

## Issues / Bug Reports

We use [GITHUB ISSUES](https://github.com/siliconcompiler/siliconcompiler/issues)
for tracking requests and bugs.

## License

[Apache License 2.0](LICENSE)
