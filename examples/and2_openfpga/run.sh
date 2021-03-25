#!/usr/bin/env bash

sc examples/and2_openfpga/and2.v \
    -target "openfpga" \
    -fpga_xml examples/and2_openfpga/k6_frac_N10_40nm_vpr.xml  \
    -fpga_xml examples/and2_openfpga/k6_frac_N10_40nm_openfpga.xml \
    -stop 'apr'
