#!/bin/sh
# The version this checkout's SiliconCompiler reports, worked out with git alone.
#
# It exists because a git worktree cannot be versioned from inside a container:
# its .git is a 64-byte file pointing at the main checkout, which is not in the
# build context. Rather than install setuptools_scm on the host to ask it, this
# reproduces the one number that matters, using git alone.
#
# 🔴 That number is the last TAG, and not the next-dev version setuptools_scm
# derives -- because `siliconcompiler.__version__` is `__base_version__`, which
# setuptools_scm sets to the tag and leaves alone for every commit after it.
# So a normal checkout 42 commits past v0.38.9 reports 0.38.9, and the image
# built from it has to report 0.38.9 too:
#
#   v0.38.9-42-g3ff1d8d0d  ->  0.38.9
#
# ⚠️ Getting this wrong is not cosmetic, and it was wrong. Emitting
# 0.38.10.dev42 made the image advertise a version the very checkout that built
# it never sends, so `GET /v1` offered `siliconcompiler 0.38.10.dev42`, the
# client declared 0.38.9, and every submit from the machine running the rig was
# refused with `version-skew` and told to install a version this server
# accepts. There was none to install.
#
# ⚠️ The cost, stated: the image no longer names which commit it holds. That is
# what the digest is for, and the digest is what gets registered and what
# actually runs -- see publish.sh. `git describe` below is echoed to stderr so
# the build log still says.
set -eu

described=$(git describe --tags --long --match 'v[0-9]*') || {
    echo "no version tag to derive from" >&2
    exit 1
}

echo "building $described" >&2
echo "$described" | sed -E 's/^v//; s/-[0-9]+-g[0-9a-f]+$//'
