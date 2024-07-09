#!/usr/bin/env bash

# Trick to get this script's directory so that we can run
# this file from project root.
# https://stackoverflow.com/a/246128
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

sc -design heartbeat \
   $SCRIPT_DIR/heartbeat.v \
   $SCRIPT_DIR/heartbeat.sdc \
   -target "freepdk45_demo"
