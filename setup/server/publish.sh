#!/bin/sh
# Build this stack's images, push them to its registry, and register them.
#
#   setup/server/publish.sh
#
# Two images, which is the point rather than a convenience:
#
#   sc-runtime   SiliconCompiler and the Slurm client, no EDA tools (~0.5 GB)
#   sc-tools     the stack's own image: the same SiliconCompiler, plus the
#                tools (~6.5 GB)
#
# 🔴 That pair is what the per-node resolution is for. A node that runs no tool
# resolves to the small one, because among the images that satisfy it the one
# with the FEWEST declared contents wins -- so an import node does not pull six
# gigabytes to run thirty seconds of Python. There is no flag for it: an image
# whose contents are framework distributions and no tool already is the
# python-only one.
#
# 🔴 Why a registry at all: an image built locally has no repository digest. The
# digest is what an operator approves and what actually runs, so registering one
# that has none is refused rather than recorded as something it is not.
#
# This registers as well as publishes, deliberately. The alternative -- printing
# commands to paste -- is how the tool list gets out of step with the image, and
# a tool that is in the image and not in the registry is the sharpest edge here:
# nobody registered it, so it raises no requirement, so its node falls back to
# the framework image and fails inside a container that never had it.
set -eu

cd "$(dirname "$0")"

STACK=${STACK:-sc-server-slurm:local}
SERVER=${SERVER:-sc-server-slurm-scserver-1}
DATADIR=${DATADIR:-/sc_server}
# The shared tree, as a volume rather than through the server container, and
# the network the cluster reaches its registry on. Both are named after the
# compose project, which docker-compose.yml pins.
#
# ⚠️ The network is not optional: staging a bundle pulls from `registry:5000`,
# which is a compose service name and resolves on that network and nowhere
# else. A container started outside it registers the image and then fails to
# fetch it, leaving a row whose bytes are not there.
DATAVOL=${DATAVOL:-sc-server-slurm_sc-server-data}
DATANET=${DATANET:-sc-server-slurm_default}

# Every tool a flow might use has to be declared. These are what asicflow needs.
TOOLS=${TOOLS:-klayout openroad opensta slang surelog yosys}

if ! docker image inspect "$STACK" >/dev/null 2>&1; then
    echo "$STACK is not built: run setup/server/compose.sh up --build first" >&2
    exit 1
fi
if ! curl -sSf -m 5 http://localhost:5000/v2/ >/dev/null 2>&1; then
    echo "no registry on localhost:5000: run setup/server/compose.sh up -d" >&2
    exit 1
fi
# 🔴 Not a precondition, and that is a fix rather than a relaxation. A
# deployment with `containers: true` and an empty registry REFUSES TO START --
# deliberately, because on it nothing could ever be dispatched -- so the one
# moment this script is most needed is the one where there is no container to
# exec into. Requiring the server to be up made that a deadlock: the server
# will not start until the registry is populated, and the registry could only
# be populated through the server.
if ! docker exec "$SERVER" true >/dev/null 2>&1; then
    echo "$SERVER is not running; registering against the volume instead" >&2
fi

echo "building sc-runtime (no EDA tools) from $STACK" >&2
docker build -f Dockerfile.runtime --build-arg "SC_STACK_IMAGE=$STACK" \
    -t sc-runtime:local . >&2

version=$(docker run --rm --entrypoint python3 sc-runtime:local \
    -c 'import siliconcompiler; print(siliconcompiler.__version__)')

# Every tool is declared at the SiliconCompiler version, because that is what
# identifies this image: the tools in it are whichever ones sc_tools shipped
# for this release, and asking each binary its own version would record five
# numbers that answer a question nobody is asking. A tool requirement resolves
# by NAME -- SiliconCompiler does not know a tool's version until the node
# runs, so a client never names one -- and the version string only has to exist
# and be stable.
#
# ⚠️ A real deployment with a curated registry records real tool versions,
# because there the operator is choosing between them.

push() {
    docker tag "$1" "localhost:5000/$2:local"
    docker push "localhost:5000/$2:local" >/dev/null
    docker image inspect "localhost:5000/$2:local" \
        --format '{{index .RepoDigests 0}}' | sed 's/.*@//'
}

# What the CLUSTER pulls is not the name the host pushed to: the host reaches
# the registry on loopback and the compute nodes reach it by service name over
# the compose network. One registry, one digest, two spellings.
runtime_digest=$(push sc-runtime:local sc-runtime)
tools_digest=$(push "$STACK" sc-tools)
echo "pushed  registry:5000/sc-runtime:local  $runtime_digest" >&2
echo "pushed  registry:5000/sc-tools:local    $tools_digest" >&2

# Registration is an operation on the DATADIR, not on the server: the registry
# tool opens the same SQLite file and holds no HTTP connection. So it runs in
# the server container when there is one, and in a throwaway container on the
# same volume when there is not.
reg() {
    if docker exec "$SERVER" true >/dev/null 2>&1; then
        docker exec "$SERVER" python3 \
            -m siliconcompiler.remote.server.registry -datadir "$DATADIR" "$@"
    else
        docker run --rm --entrypoint python3 --network "$DATANET" \
            -v "$DATAVOL:$DATADIR" "$STACK" \
            -m siliconcompiler.remote.server.registry -datadir "$DATADIR" "$@"
    fi
}

# The same, for the one thing that is not a registry command.
in_datadir() {
    if docker exec "$SERVER" true >/dev/null 2>&1; then
        # 🔴 -i, because docker exec does not attach stdin without it and a
        # heredoc fed to a program reading "-" then silently gets nothing. The
        # config is written, nothing complains, and containers stay off.
        docker exec -i "$SERVER" python3 - "$DATADIR"
    else
        docker run --rm -i --entrypoint python3 --network "$DATANET" \
            -v "$DATAVOL:$DATADIR" "$STACK" - "$DATADIR"
    fi
}

reg add-software siliconcompiler >/dev/null
reg add-version siliconcompiler "$version" >/dev/null

tools_contains=""
for tool in $TOOLS; do
    reg add-software "$tool" >/dev/null
    reg add-version "$tool" "$version" >/dev/null
    tools_contains="$tools_contains -contains $tool==$version"
done

echo "staging bundles (skopeo, then umoci -- the big one takes a minute)" >&2
reg add-image registry:5000/sc-runtime:local -digest "$runtime_digest" \
    -contains "siliconcompiler==$version" -stage >/dev/null
# shellcheck disable=SC2086
reg add-image registry:5000/sc-tools:local -digest "$tools_digest" \
    -contains "siliconcompiler==$version" $tools_contains -stage >/dev/null

in_datadir <<'PY'
import json, sys
path = sys.argv[1] + "/config.json"
config = json.load(open(path))
config["containers"] = True
json.dump(config, open(path, "w"), indent=2)
PY

# 🔴 Both, and in this order. scserver runs slurmctld, and a controller restart
# forgets every dynamic node -- "slurmd -Z" registers at startup and is named in
# no config file -- so sinfo comes back showing 0 nodes and every job queues for
# ever. Restarting the runners is what re-registers them.
echo "restarting the server, then the runners" >&2
# stop + up rather than restart, because a service that is DOWN is the case
# this has to handle: `docker compose restart` on a container that is not
# running is an error on some versions, and the server not running is exactly
# how somebody arrives here.
docker compose stop scserver scrunner >/dev/null 2>&1
docker compose up -d scserver >/dev/null 2>&1
docker compose up -d scrunner >/dev/null 2>&1

sleep 12

echo
echo "this deployment now runs jobs in containers:"
reg resolve -versions "siliconcompiler==$version" \
    $(for tool in $TOOLS; do printf -- '-tools %s ' "$tool"; done)
