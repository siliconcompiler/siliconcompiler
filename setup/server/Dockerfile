# A self-contained Slurm cluster plus sc-server, for local testing.
#
# Every service in docker-compose.yml runs this one image with a different
# role argument; see entrypoint.sh.

# Declared before the first FROM, because only a global ARG is visible to a
# later stage's FROM line. docker-compose.yml passes this through, so the image
# is normally chosen there rather than by editing this file.
#
# A whole image reference rather than a bare tag, so CI can hand over exactly
# what its docker_image job resolved -- the same value the rest of the suite
# runs against, and possibly a digest rather than a tag.
#
# Whatever is passed must carry the slurm version this repo pins, with
# slurmrestd built in: entrypoint.sh starts it, and an image predating the
# slurm bump comes up with the wrong version and no REST daemon.
ARG SC_TOOLS_IMAGE=ghcr.io/siliconcompiler/sc_tools:latest


##############################################################################
# Stage 1 -- work out the version, then build a wheel at it.
#
# The version comes from SC_VERSION, else the git tags, else the _version.py an
# editable install writes. A git worktree has no .git directory, only a file
# pointing outside the build context, so it needs the last two or SC_VERSION.
# Only the wheel crosses into the final image.
##############################################################################
FROM ubuntu:24.04 AS version

ARG DEBIAN_FRONTEND=noninteractive
ARG SC_VERSION=""

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# Mounted, not copied: only the answer is kept.
RUN --mount=type=bind,target=/ctx set -eu; \
    version="$SC_VERSION"; \
    if [ -z "$version" ] && [ -d /ctx/.git ]; then \
        version=$(git -c safe.directory='*' -C /ctx describe --tags \
                  --abbrev=0 --match 'v[0-9]*' | sed 's/^v//'); \
    fi; \
    if [ -z "$version" ] && [ -f /ctx/siliconcompiler/_version.py ]; then \
        version=$(sed -n 's/^__base_version__ = "\(.*\)"$/\1/p' \
                  /ctx/siliconcompiler/_version.py); \
    fi; \
    if [ -z "$version" ]; then \
        echo "Cannot work out the version: pass SC_VERSION=<x.y.z>" >&2; \
        exit 1; \
    fi; \
    echo "$version" > /version

FROM ubuntu:24.04 AS wheel

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /build && /build/bin/pip install --no-cache-dir build

COPY --from=version /version /version
COPY pyproject.toml README.md LICENSE MANIFEST.in /src/
COPY siliconcompiler /src/siliconcompiler

RUN set -eu; \
    export SETUPTOOLS_SCM_PRETEND_VERSION="$(cat /version)"; \
    cd /src; \
    /build/bin/python -m build --wheel --outdir /wheels


##############################################################################
# Stage 2 -- the cluster image.
#
# sc_tools brings slurm, slurmrestd, the EDA tools, munge, git and an Ubuntu
# 24.04 userland. sc_tools rather than sc_runner: the two are the same except
# that sc_runner also pip-installs a released siliconcompiler, which this
# image would immediately overwrite with the wheel from stage 1.
##############################################################################
FROM ${SC_TOOLS_IMAGE}

# The virtualenv siliconcompiler lives in, ahead of everything on PATH: the
# compute node's run script invokes plain "python3" and has to get this one.
# (Ubuntu 24.04 is PEP 668 externally-managed, so a venv rather than pip3 into
# the system interpreter.)
RUN python3 -m venv /venv
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:$PATH"

COPY --from=wheel /wheels /tmp/wheels
# [server] pulls Flask, which sc-server needs and a default install omits.
# The glob goes through echo because an extra cannot be appended to a pattern,
# and stage 1 builds exactly one wheel.
RUN pip install --no-cache-dir --upgrade "$(echo /tmp/wheels/*.whl)[server]" \
    && rm -rf /tmp/wheels

# Nothing to set up for slurm here: the base image's install-slurm.sh already
# creates the "slurm" and "slurmrestd" accounts and the slurm-owned
# /sc_tools/{etc,spool/slurm,spool/slurmd} that this cluster's slurm.conf
# names.

# NOTE: no munge key is baked in. Every slurm daemon has to share one, and an
# image-baked key is silently wrong here: any repo edit invalidates the wheel
# layer and everything after it, so each rebuild would mint a new key, and
# rebuilding one service would leave it unable to talk to the others
# ("Munge decode failed: Invalid credential"). entrypoint.sh creates the key in
# a volume shared by all of them instead.

# cgroup.conf overrides the base image's, which disables cgroups entirely --
# see the file for what this stack needs instead, and why.
COPY setup/server/slurm.conf /sc_tools/etc/slurm.conf
COPY setup/server/cgroup.conf /sc_tools/etc/cgroup.conf
COPY setup/server/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /sc_server
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
