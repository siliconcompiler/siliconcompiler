# SiliconCompiler

![CI Tests](https://github.com/zeroasiccorp/siliconcompiler/workflows/CI%20Tests/badge.svg)

The SiliconCompiler project aims to enable fully automated translation of high level source code into hardware.

## Resources

- **Website:** https://www.siliconcompiler.com
- **Documentation:** https://www.siliconcompiler.com/docs
- **Community:** https://www.siliconcompiler.com/community

## Installation
```sh
$ git clone https://github.com/siliconcompiler/siliconcompiler
$ cd siliconcompiler
$ pip install -r requirements.txt
$ python -m pip install -e .
```

## Pre-requisites
The open source SiliconCompiler flow depends on a number of open source technologies. Full installation support of these tools is out of scope of for the project, Ubuntu based install scripts can be found in the [./setup](setup) directory for convencience.

- **OpenRoad:** https://github.com/The-OpenROAD-Project/OpenROAD
- **OpenSTA:** https://github.com/The-OpenROAD-Project/OpenSTA
- **ABC**: https://github.com/berkeley-abc/abc
- **Yosys:** https://github.com/YosysHQ/yosys
- **Verilator:** https://github.com/verilator/verilator
- **Klayout:** https://github.com/KLayout/klayout
- **VTR:** https://github.com/verilog-to-routing/vtr-verilog-to-routing

## Testing installation

```bash
$ ./examples/gcd/run.sh
$ ./examples/gcd/run_remote.sh
```
This will produce a GDSII output at `build/gcd/job1/export/outputs/gcd.gds`, which can then be viewed in KLayout.

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
>>> chip.set('target', 'freepdk45_asic')
>>> chip.set('asic', 'diesize', "0 0 100.13 100.8")
>>> chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
>>> chip.target()
>>> chip.run()
>>> chip.summary()
>>> chip.display()
```
## Continuous build status
(place holder)

## Contributing
(place holder)

## License
TBD



