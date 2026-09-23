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
# Stage 1 -- build a wheel with a real version.
#
# siliconcompiler's version is derived from git by setuptools_scm, so this
# stage takes the whole context including .git and lets it do that properly.
# Only the wheel crosses into the final image, so the history does not ship.
#
# It cannot be skipped by inventing a version: lambdapdk requires
# siliconcompiler>=0.38.5, so a placeholder makes pip's resolver refuse.
#
# 🔴 A git WORKTREE has no .git directory -- it has a 64-byte file pointing at
# one in the main checkout, which is outside the build context and therefore
# unreachable from in here. setuptools_scm then fails with a TypeError out of
# _version_missing() that names neither git nor the worktree. SC_VERSION is the
# way through: pass the version the host resolved and this stage does not ask
# git anything. setup/server/compose.sh works it out and passes it for you.
##############################################################################
FROM ubuntu:24.04 AS wheel

ARG DEBIAN_FRONTEND=noninteractive
ARG SC_VERSION=""

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY . /src
RUN set -eu; \
    if [ -n "$SC_VERSION" ]; then \
        # Told what this is, so git is not consulted at all. The repository is
        # removed rather than left in place: setuptools_scm prefers what it can
        # read over what it was told, and in a worktree what it can read is a
        # pointer to somewhere that does not exist here.
        rm -rf /src/.git; \
        export SETUPTOOLS_SCM_PRETEND_VERSION="$SC_VERSION"; \
    elif [ -f /src/.git ]; then \
        echo "This context is a git worktree: .git is a pointer to a directory" >&2; \
        echo "outside it, so setuptools_scm cannot derive a version in here." >&2; \
        echo "Build through setup/server/compose.sh, or pass the version:" >&2; \
        echo "  SC_VERSION=\$(setup/server/scversion.sh) docker compose build" >&2; \
        exit 1; \
    fi; \
    python3 -m venv /build; \
    /build/bin/pip install --no-cache-dir build; \
    cd /src; \
    /build/bin/python -m build --wheel --outdir /wheels; \
    ls -l /wheels


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
# [server] pulls Flask, which the server needs and a default install omits.
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

# Running a job inside a registered image needs three things the base image
# does not carry, and none of them is a container daemon:
#
#   crun     the OCI runtime Slurm invokes for "srun --container". A binary it
#            execs, so no socket, no daemon and no privilege beyond the task's
#   skopeo   copies an image out of a registry into an OCI layout
#   umoci    unpacks that layout into the bundle crun runs
#
# 🔴 Deliberately NOT docker or podman. Handing a compute node the ability to
# start containers on the host is a much larger grant than running a flow, and
# Slurm's own container support exists precisely so that grant is unnecessary.
RUN apt-get update && apt-get install -y --no-install-recommends \
        crun skopeo umoci \
    && rm -rf /var/lib/apt/lists/*

# cgroup.conf overrides the base image's, which disables cgroups entirely --
# see the file for what this stack needs instead, and why.
COPY setup/server/slurm.conf /sc_tools/etc/slurm.conf
COPY setup/server/cgroup.conf /sc_tools/etc/cgroup.conf
COPY setup/server/oci.conf /sc_tools/etc/oci.conf
COPY setup/server/registries.conf /etc/containers/registries.conf
COPY setup/server/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /sc_server
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
