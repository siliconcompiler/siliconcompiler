#!/bin/sh
# The version setuptools_scm would derive, worked out with git alone.
#
# It exists because a git worktree cannot be versioned from inside a container:
# its .git is a 64-byte file pointing at the main checkout, which is not in the
# build context. Rather than install setuptools_scm on the host to ask it, this
# reproduces its default "guess-next-dev" rule -- the patch level of the last
# tag, plus one, plus the number of commits since.
#
#   v0.38.9-25-g3ff1d8d0d  ->  0.38.10.dev25
#
# The local segment (+g<hash>) is deliberately left off: it is what makes two
# builds of the same commit produce differently-named wheels, and the image is
# already identified by its tag.
set -eu

described=$(git describe --tags --long --match 'v[0-9]*') || {
    echo "no version tag to derive from" >&2
    exit 1
}

echo "$described" | sed -E 's/^v//' | awk -F'-' '{
    split($1, v, ".")
    printf "%s.%s.%s.dev%s\n", v[1], v[2], v[3] + 1, $2
}'
