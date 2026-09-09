# The accounts the daemons run as. Both are service accounts that are never
# logged into, so both are --system: that keeps them in the system UID range
# instead of taking a UID from the range real users are assigned from.
#
# SlurmUser, which slurmctld drops to.
useradd --system --no-create-home --shell /usr/sbin/nologin slurm

# slurmrestd refuses to run as root, as SlurmUser or as nobody, so it needs an
# account of its own (src/slurmrestd/slurmrestd.c, _check_user()).
useradd --system --no-create-home --shell /usr/sbin/nologin slurmrestd

# Configure Slurm
mkdir -p /sc_tools/log/slurm /sc_tools/spool/slurm /sc_tools/spool/slurmd /sc_tools/etc
chown -R slurm:slurm /sc_tools/log/slurm /sc_tools/spool/slurm /sc_tools/spool/slurmd /sc_tools/etc

mv /sc_tools/slurm_cfg/cgroup.conf /sc_tools/etc/
