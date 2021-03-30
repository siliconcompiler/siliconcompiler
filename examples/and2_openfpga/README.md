# AND2 Example

This is an example for testing the OpenFPGA bitstream generation flow. 

## Prerequisites

This flow requires installing OpenFPGA as follows:
``` sh
git clone https://github.com/LNIS-Projects/OpenFPGA.git && cd OpenFPGA
make all
```

See the [OpenFPGA
docs](https://openfpga.readthedocs.io/en/master/tutorials/getting_started/compile/)
for more detailed compilation instructions.

You must also add `$OPENFPGA_DIR/openfpga` to your path, where `$OPENFPGA_DIR`
points to your local clone of the OpenFPGA git repo.

## How to run

Execute `./examples/and2_fpga/run.sh` from the `siliconcompiler/` root
directory.

## Acknowledgements

The source file (`and2.v`) in this directory is copied directly from an
[OpenFPGA example](https://github.com/lnis-uofu/OpenFPGA/blob/master/openfpga_flow/benchmarks/micro_benchmark/and2/and2.v).


