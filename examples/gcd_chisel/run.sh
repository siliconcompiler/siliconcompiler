#!/bin/bash

sc -input "hll scala GCD.scala" -frontend chisel
sc-show -design GCD
