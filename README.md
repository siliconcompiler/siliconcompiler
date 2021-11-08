
![alt text](docs/_images/sc_logo_with_text.png)

[![Quick CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/on_push_tests.yml)
[![Daily CI Tests](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/daily_tests.yml)
[![Documentation](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml/badge.svg)](https://github.com/siliconcompiler/siliconcompiler/actions/workflows/docs_test.yml)

SiliconCompiler (“SC”) is a open source hardware compiler infrastructure project. The goal of the SiliconCompiler project is to lower the barrier to hardware specialization.

- **Website:** https://www.siliconcompiler.com
- **Documentation:** https://www.siliconcompiler.com/docs
- **Community:** https://siliconcompiler.com/community
- **Sources:** https://github.com/siliconcompiler/siliconcompiler


## Quickstart

SiliconCompiler uses a standrdized schema to control and track all compiler
tasks. For simple designs, we only need to define a small set of parameters.
The basic compilation workflow includes the following steps:

 1. Create a SiliconCompiler object.
 2. Set up design and compilation parameters.
 3. Run compilation.
 4. Inspect results.

The code snippet below illstrates the basics. For the complete
example and the rest of the documentation, [read the docs](https://www.siliconcompiler.com/docs).

```python
import siliconcompiler                        # import python package
chip = siliconcompiler.Chip()                 # create chip object
chip.add('source', 'heartbeat.v')             # define list of sources
chip.set('design', 'heartbeat')               # set top module name
chip.clock(name='clk', pin='clk', period=1.0) # define a clock
chip.target('asicflow_freepdk45')             # load pre-defined flow
chip.run()                                    # run compilation
chip.summary()                                # print run summary
chip.show()                                   # show layout
```

## Installation

SiliconCompiler is availabe as wheel packages for macOS, Windows and Linux on PyPI.
To install the current release:

```sh
  python -m pip install siliconcompiler
```

To install from repository:

```bash
 git clone https://github.com/siliconcompiler/siliconcompiler
 cd siliconcompiler
 pip install -r requirements.txt
 python -m pip install -e .
```

## Contributing
If you want to contribute to SiliconCompiler, be sure to review the [contributing guidelines](./CONTRIBUTING.md)
We use GitHub issues for tracking requests and bugs.

## License
