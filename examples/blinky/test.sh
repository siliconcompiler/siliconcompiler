#!/usr/bin/env bash

sc examples/blinky/blinky.v \
    -target "ice40_nextpnr" \
    -constraint "examples/blinky/icebreaker.pcf" \
    -design "blinky"

if test -f "./build/blinky/job1/export/outputs/blinky.bit"; then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
