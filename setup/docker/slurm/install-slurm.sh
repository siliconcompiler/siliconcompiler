# Create slurm user
useradd slurm

# slurmrestd refuses to run as root, as SlurmUser or as nobody, so it needs an
# account of its own (src/slurmrestd/slurmrestd.c, _check_user()).
useradd --system --no-create-home --shell /usr/sbin/nologin slurmrestd

# Configure Slurm
mkdir -p /sc_tools/log/slurm /sc_tools/spool/slurm /sc_tools/spool/slurmd /sc_tools/etc
chown -R slurm:slurm /sc_tools/log/slurm /sc_tools/spool/slurm /sc_tools/spool/slurmd /sc_tools/etc

mv /sc_tools/slurm_cfg/cgroup.conf /sc_tools/etc/
