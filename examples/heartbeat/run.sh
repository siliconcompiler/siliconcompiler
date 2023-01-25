#!/bin/bash

sc -design heartbeat \
   heartbeat.v \
   heartbeat.sdc \
   -target "freepdk45_demo"
