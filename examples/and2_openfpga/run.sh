#!/usr/bin/env bash

sc examples/and2_openfpga/and2.v \
    -fpga_arch examples/and2_openfpga/k6_frac_N10_40nm_openfpga.xml \
    -fpga_arch examples/and2_openfpga/k6_frac_N10_40nm_vpr.xml \
    -mode "fpga" \
    -target "fpgaflow_openfpga" \
    -design "and2"
