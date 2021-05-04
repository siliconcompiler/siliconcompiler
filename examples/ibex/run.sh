#!/bin/sh
#set -x

OPT=$1
NICKNAME="ibex"
DESIGN="ibex_core"
TARGET="freepdk45"
DIESIZE="0 0 600.08 599.8"
CORESIZE="10.07 11.2 590.01 590"

sc "examples/$NICKNAME/$DESIGN.v" \
   -nickname "$NICKNAME" \
   -design "ibex_core" \
   -y "examples/$NICKNAME" \
   -target "$TARGET" \
   -constraint "examples/$NICKNAME/$DESIGN.sdc" \
   -asic_diesize "$DIESIZE" \
   -asic_coresize "$CORESIZE" \
   -loglevel "INFO" \
   -quiet -relax $OPT
