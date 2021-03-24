#!/usr/bin/env bash

sc examples/blinky/blinky.v \
    -target "ice40" \
    -constraint "examples/blinky/icebreaker.pcf"
