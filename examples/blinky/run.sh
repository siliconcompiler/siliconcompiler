#!/usr/bin/env bash

sc examples/blinky/blinky.v \
    -target "ice40_nextpnr" \
    -constraint "examples/blinky/icebreaker.pcf" \
    -design "blinky"
