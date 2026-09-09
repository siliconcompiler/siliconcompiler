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
#
# runuser, not "su -c": su replaces PATH with the login.defs default for the
# target user, which does not contain /sc_tools/sbin, so the daemon is reported
# as "slurmrestd: not found". runuser keeps the environment, and the binary is
# resolved here anyway while PATH is still root's.
#
# SLURMRESTD_SECURITY turns off two things slurmrestd does to itself at
# startup: unshare(CLONE_SYSVSEM) and unshare(CLONE_FILES), which detach it
# from the System V semaphore adjustments and the file-descriptor table it
# inherited from its parent. Docker's default seccomp profile refuses unshare
# without CAP_SYS_ADMIN, so without this the daemon exits with "Unable to
# unshare System V namespace: Operation not permitted".
#
# It is the narrowest of the three ways out. The alternatives -- seccomp=unconfined
# or CAP_SYS_ADMIN, both verified to work -- weaken the whole container's
# sandbox to keep two hardening steps inside one daemon, whose parent here is
# an entrypoint shell with nothing worth isolating from anyway.
#
# Note what is NOT set: disable_user_check, the dangerous member of this family,
# which slurmrestd itself refuses on release builds ("will allow anyone to run
# any command on the cluster as root"). Authentication, authorization and the
# account the daemon runs under are all unchanged -- it still refuses to run as
# root or as SlurmUser.
slurmrestd_bin=$(command -v slurmrestd || true)
if [ -n "$slurmrestd_bin" ]; then
    SLURMRESTD_SECURITY=disable_unshare_sysv,disable_unshare_files \
        runuser -u slurmrestd -- "$slurmrestd_bin" 0.0.0.0:6820 &
else
    echo "NOTE: slurmrestd was not built into this image" >&2
fi
