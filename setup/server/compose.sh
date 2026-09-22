#!/bin/sh
# docker compose, with the version worked out first.
#
#   setup/server/compose.sh up --build
#
# Identical to running docker compose in this directory, except that it exports
# SC_VERSION when the checkout is a git worktree. See scversion.sh for why a
# worktree needs one and a normal checkout does not.
set -eu

cd "$(dirname "$0")"

if [ -z "${SC_VERSION:-}" ] && [ -f ../../.git ]; then
    SC_VERSION=$(./scversion.sh)
    export SC_VERSION
    echo "building a git worktree as siliconcompiler $SC_VERSION" >&2
fi

exec docker compose "$@"
