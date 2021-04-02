#!/usr/bin/env bash

sc examples/blinky/blinky.v \
    -target "ice40_nextpnr" \
    -constraint "examples/blinky/icebreaker.pcf"

if test -f "./build/export/job1/outputs/blinky.bit"; then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
