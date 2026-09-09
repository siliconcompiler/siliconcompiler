#!/bin/bash

# Set the container's hostname in slurm.conf
sed "s^{{ hostname }}^`hostname`^g" /sc_tools/slurm_cfg/slurm.conf.in > /sc_tools/etc/slurm.conf

# slurmrestd authenticates over TCP with auth/jwt, which needs a signing key
# shared with slurmctld. Generate it per container rather than baking a shared
# secret into the published image.
if [ ! -f /sc_tools/etc/jwt_hs256.key ]; then
    dd if=/dev/urandom of=/sc_tools/etc/jwt_hs256.key bs=32 count=1 2>/dev/null
    chown slurm:slurm /sc_tools/etc/jwt_hs256.key
    chmod 0600 /sc_tools/etc/jwt_hs256.key
fi

# Start munge and slurm daemons
/etc/init.d/munge start
slurmctld
slurmd

# Start the REST API. Nothing in SiliconCompiler calls it yet -- it is built and
# run so the endpoint exists and is exercised by CI. It cannot run as root or as
# SlurmUser, hence the dedicated account from install-slurm.sh.
if command -v slurmrestd >/dev/null 2>&1; then
    su -s /bin/sh -c "slurmrestd 0.0.0.0:6820" slurmrestd &
fi
