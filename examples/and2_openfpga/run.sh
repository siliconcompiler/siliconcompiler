#!/usr/bin/env bash

sc examples/and2_openfpga/and2.v \
    -mode "fpga" \
    -fpga_xml examples/and2_openfpga/k6_frac_N10_40nm_vpr.xml  \
    -openfpga_xml examples/and2_openfpga/k6_frac_N10_40nm_openfpga.xml \
    -openfpga_sim examples/and2_openfpga/auto_sim_openfpga.xml
