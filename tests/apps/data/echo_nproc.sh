#!/bin/sh

echo "ECHO NPROC: ${NPROC:-$(nproc)}"
echo "PREFIX: $PREFIX"
echo "USE_SUDO_INSTALL: $USE_SUDO_INSTALL"
