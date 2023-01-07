#!/bin/bash

sc heartbeat.v \
  heartbeat.sdc \
  -design heartbeat \
  -target "freepdk45_demo"
