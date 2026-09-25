# A self-contained Slurm cluster plus sc-server, for local testing.
#
# Two images out of one build graph: `cluster` is what every slurm service
# and the server run, with a different role argument (see entrypoint.sh), and
# `runtime` is the framework image a node with no EDA tool resolves to.
# docker-compose.yml names both with `target:`.

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
# 🔴 **The version is pinned to the last TAG, on every path, and that is not a
# shortcut.** `siliconcompiler.__version__` is setuptools_scm's
# `__base_version__`, which stays at the tag for every commit after it -- so a
# checkout 42 commits past v0.38.9 reports 0.38.9 and an image built from it
# has to report 0.38.9 too. Letting scm derive 0.38.10.dev42 here made the
# server advertise a version the very checkout that built it never sends, and
# every submit from that machine was refused with `version-skew` and told to
# install a version that does not exist.
#
# ⚠️ A git WORKTREE has no .git directory -- it has a 64-byte file pointing at
# one in the main checkout, which is outside the build context and therefore
# unreachable from in here. That is why `_version.py` is the second source: an
# editable install has already written the answer into the tree, and reading it
# is what lets a worktree build with plain `docker compose up`.
##############################################################################
FROM ubuntu:24.04 AS wheel

ARG DEBIAN_FRONTEND=noninteractive
ARG SC_VERSION=""

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY . /src
RUN set -eu; \
    version="$SC_VERSION"; \
    if [ -z "$version" ] && [ -d /src/.git ]; then \
        version=$(git -C /src describe --tags --abbrev=0 --match 'v[0-9]*' \
                  | sed 's/^v//'); \
    fi; \
    if [ -z "$version" ] && [ -f /src/siliconcompiler/_version.py ]; then \
        version=$(sed -n 's/^__base_version__ = "\(.*\)"$/\1/p' \
                  /src/siliconcompiler/_version.py); \
    fi; \
    if [ -z "$version" ]; then \
        echo "Cannot work out what version this is. There is no .git" >&2; \
        echo "directory here (a worktree's .git points outside the build" >&2; \
        echo "context) and no siliconcompiler/_version.py, which an editable" >&2; \
        echo "install writes. Either install the package once, or pass it:" >&2; \
        echo "  SC_VERSION=0.38.9 docker compose build" >&2; \
        exit 1; \
    fi; \
    echo "building siliconcompiler $version"; \
    # Removed rather than left in place: setuptools_scm prefers what it can
    # read over what it was told, and what it would read is the dev version
    # this stage exists to avoid.
    rm -rf /src/.git; \
    export SETUPTOOLS_SCM_PRETEND_VERSION="$version"; \
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
FROM ${SC_TOOLS_IMAGE} AS cluster

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
COPY setup/server/bootstrap.py /usr/local/bin/sc-bootstrap
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/sc-bootstrap

WORKDIR /sc_server
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]


##############################################################################
# Stage 3 -- the framework image.
#
# SiliconCompiler with no EDA tools, for the nodes that do not run one.
#
# 🔴 This is the image the whole per-node resolution exists for. A 42-node flow
# over six tools has a lot of nodes that run thirty seconds of Python -- import,
# the builtin joins and minimums, export -- and one image per job makes every
# one of them pull the twelve-gigabyte container that OpenROAD lives in. Here
# they pull this instead, and the server picks between them with no flag to set:
# among the images that satisfy a node, the one with the FEWEST declared
# contents wins, and an image whose contents are framework distributions and no
# tool already is the python-only one.
#
# ⚠️ It is not python-ONLY in the literal sense, and cannot be. A framework
# image drives the flow it was given -- it submits every node to Slurm -- so it
# needs the Slurm client. That is ~10 MB of plugins beside libslurm, taken from
# the same build the cluster runs so the versions cannot drift, against ~6 GB of
# EDA tools left behind.
#
# A `target:` rather than a Dockerfile of its own, so the two images share
# one build graph: this stage copies out of `cluster` and buildx resolves
# the order itself. docker-compose.yml builds both.
##############################################################################
FROM ubuntu:24.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive

# 🔴 git is not optional, and its absence is the least obvious failure here.
# SiliconCompiler depends on GitPython, which refuses to IMPORT without a git
# executable -- so a runtime image without it dies before the run starts, with
# a page of GitPython advice about $GIT_PYTHON_REFRESH and nothing that mentions
# SiliconCompiler.
#
# libmunge2 because slurm authenticates with munge, which its auth plugin
# dlopens rather than links; without it srun fails with "authentication plugin".
#
# 🔴 graphviz because the PYTHON distribution of that name is a wrapper: it
# shells out to `dot`. It arrives with siliconcompiler, so this image declares
# it and nodes that need it are placed here rather than in the twelve-gigabyte
# tool image -- and without the binary that placement is a container that
# cannot run what the registry says it holds.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git python3 python3-venv libmunge2 graphviz \
    && rm -rf /var/lib/apt/lists/*

# SiliconCompiler, exactly as the stack built it -- the same wheel, the same
# resolved dependencies. Copying the venv rather than rebuilding is what makes
# the version in this image identical to the one the server advertises, which
# is the property the registry is keeping a record of.
COPY --from=cluster /venv /venv

# The Slurm client from the same build the cluster runs. A client and a
# controller that disagree about the protocol fail in ways that read like a
# network problem, so this is a copy and never an apt install.
COPY --from=cluster /sc_tools/lib/slurm /sc_tools/lib/slurm
COPY --from=cluster /sc_tools/lib/libslurm.so* /sc_tools/lib/
COPY --from=cluster /sc_tools/bin/srun /sc_tools/bin/sbatch /sc_tools/bin/scontrol \
                  /sc_tools/bin/sinfo /sc_tools/bin/squeue /sc_tools/bin/scancel \
                  /sc_tools/bin/sacct /sc_tools/bin/salloc /sc_tools/bin/
COPY --from=cluster /sc_tools/etc/slurm.conf /sc_tools/etc/slurm.conf

# slurm.conf names SlurmUser, and every slurm command resolves it while reading
# the file -- so without this account even "srun --version" dies with "Invalid
# user for SlurmUser slurm" before it does anything. The ids match the stack's
# because a uid is what the cluster compares, not a name.
RUN groupadd -g 996 slurm && useradd -u 999 -g 996 -M -s /usr/sbin/nologin slurm

ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:/sc_tools/bin:$PATH"
ENV LD_LIBRARY_PATH="/sc_tools/lib"

WORKDIR /sc_server


##############################################################################
# Stage 4 -- the server image.
#
# slurmctld, slurmdbd, slurmrestd and the SiliconCompiler server, with no EDA
# tools. A controller is not an EDA machine: it schedules, it answers HTTP and
# it unpacks bundles, and the ~6 GB of tools in the cluster image are dead
# weight in every container that is not a compute node.
#
# 🔴 **What this saves and what it does not, said plainly.** It does not remove
# a build: `sc-tools` still has to be built and pushed, because that is what a
# node's task runs inside. It does not free disk while `scrunner` runs the
# cluster image, since docker shares the layers either way. What it buys is a
# server container of a few hundred megabytes rather than seven gigabytes, a
# much faster rebuild when only SiliconCompiler changed, and a controller whose
# image contains nothing it could accidentally run.
#
# Built on `runtime`, which already carries the venv, the Slurm CLIENT and the
# slurm account -- so what is added here is the daemons and what they dlopen.
##############################################################################
FROM runtime AS server

ARG DEBIAN_FRONTEND=noninteractive

# 🔴 The library list is not guesswork and not a superset: it is `ldd` over
# /sc_tools/sbin/* and every plugin in /sc_tools/lib/slurm, minus what
# ubuntu:24.04 already has. Slurm dlopens its plugins, so a missing one of
# these is not a link error at build time -- it is a daemon that starts and
# then cannot do one thing, which reads like a configuration problem.
#
#   libmariadb3        accounting_storage/mysql, which only slurmdbd loads
#   libjwt2 libjansson4 libhttp-parser2.9 libyaml-0-2 libjson-c5   slurmrestd
#   libmunge2          auth/munge, which is every daemon's authentication
#   libb64-0d libgcrypt20 libdbus-1-3 libcap2 liblz4-1 libzstd1    the rest
#
# skopeo and umoci because the API process stages the framework bundle at
# submit: `sbatch --container` names a bundle that has to exist before the job
# starts. crun is deliberately NOT here -- nothing in this image runs a
# container, and the compute node is where that belongs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        munge skopeo umoci \
        libmariadb3 libjwt2 libjansson4 libhttp-parser2.9 libyaml-0-2 \
        libjson-c5 libb64-0d libgcrypt20 libdbus-1-3 libcap2 liblz4-1 libzstd1 \
    && rm -rf /var/lib/apt/lists/*

# 🔴 The munge account is moved onto the cluster image's ids, and this is not
# tidiness. Every daemon in the stack shares ONE munge key, on a volume, and
# munged refuses a key it does not own -- while entrypoint.sh chowns that key
# to the local munge user on every start. Two containers disagreeing about the
# uid means each one takes the key away from the other, and the symptom is
# "Munge decode failed: Invalid credential" somewhere else entirely.
RUN groupmod -g 101 munge \
    && usermod -u 100 -g 101 munge \
    && groupadd -g 995 slurmrestd \
    && useradd -u 996 -g 995 -M -s /usr/sbin/nologin slurmrestd \
    && chown -R munge:munge /etc/munge /var/lib/munge /var/log/munge

# The daemons themselves -- 2 MB -- and the plugins they dlopen. /sc_tools/lib
# is 188 MB in the cluster image and 10 MB of it is slurm's; this takes the
# 10 MB.
COPY --from=cluster /sc_tools/sbin /sc_tools/sbin
COPY --from=cluster /sc_tools/lib/slurm /sc_tools/lib/slurm

# StateSaveLocation and the job/node state files slurmctld writes into it, plus
# the JWT signing key the ctld role generates. Owned by slurm, which is what
# slurmctld checks before it will start.
RUN mkdir -p /sc_tools/spool/slurm /sc_tools/spool/slurmd /sc_tools/log \
    && chown -R slurm:slurm /sc_tools/spool /sc_tools/log

COPY setup/server/slurm.conf /sc_tools/etc/slurm.conf
COPY setup/server/cgroup.conf /sc_tools/etc/cgroup.conf
COPY setup/server/oci.conf /sc_tools/etc/oci.conf
COPY setup/server/registries.conf /etc/containers/registries.conf
COPY setup/server/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY setup/server/bootstrap.py /usr/local/bin/sc-bootstrap
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/sc-bootstrap

ENV PATH="/venv/bin:/sc_tools/sbin:/sc_tools/bin:$PATH"

WORKDIR /sc_server
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
