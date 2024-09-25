#!/usr/bin/env bash

set -e
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-openfpga.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-bambu.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-sv2v.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-yosys.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-netgen.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-chisel.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-montage.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-klayout.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-vpr.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-bluespec.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-magic.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-verible.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-xyce.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-slurm.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-verilator.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-ghdl.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-surelog.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-slang.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-icepack.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-icarus.sh"
docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-openroad.sh"

# Skip due to yosys dependency
#docker build .. --file Docker.testbuild --build-arg="SC_INSTALL_SCRIPT=install-nextpnr.sh"