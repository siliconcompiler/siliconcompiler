#!/usr/bin/env bash

# When run from the root of the repository, formats Verilog using verible to ensure that formatting
# CI checks pass.

set -e

FILES=$(mktemp /tmp/format-verilog.XXXXXX)

# Collect all Verilog files, but generally ignore things that are copied verbatim from third party
# sources.
# tests/flows/data/bad.v is ours, but intentionally contains invalid syntax
find . \( \
    -name "*.v" \
    -or -name "*.sv" \
    -or -name "*.vh" \
    -or -name "*.svh" \
\) -not \( \
    -path "./third_party/*" \
    -or -path "*build/*" \
    -or -path "./siliconcompiler/tools/yosys/vpr_yosyslib/*" \
    -or -path "./tests/flows/data/sv/*" \
    -or -path "./examples/aes/aes.v" \
    -or -path "./examples/spree/spree.v" \
    -or -path "./examples/picorv32/picorv32.v" \
    -or -path "./tests/flows/data/bad.v" \
\) >> $FILES

verible-verilog-format \
    --failsafe_success=false \
    --indentation_spaces 4 \
    --inplace `cat $FILES`

cat $FILES
rm $FILES
