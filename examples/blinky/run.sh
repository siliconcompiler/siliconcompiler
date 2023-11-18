#!/usr/bin/env bash

# Trick to get this script's directory so that we can run
# this file from project root.
# https://stackoverflow.com/a/246128
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

sc $SCRIPT_DIR/blinky.v $SCRIPT_DIR/icebreaker.pcf \
   -fpga_partname "ice40up5k-sg48" \
   -target "fpgaflow_demo" \
   -design "blinky"
