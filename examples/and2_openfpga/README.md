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

The source files in this directory are copied directly from
[OpenFPGA](https://github.com/lnis-uofu/OpenFPGA):

- [`and2.v`](https://github.com/lnis-uofu/OpenFPGA/blob/master/openfpga_flow/benchmarks/micro_benchmark/and2/and2.v)
- [`k6_frac_N10_40nm_openfpga.xml`](https://github.com/lnis-uofu/OpenFPGA/blob/master/openfpga_flow/openfpga_arch/k6_N10_40nm_openfpga.xml)
- [`k6_frac_N10_40nm_vpr.xml`](https://github.com/lnis-uofu/OpenFPGA/blob/master/openfpga_flow/vpr_arch/k6_frac_N10_tileable_40nm.xml)
