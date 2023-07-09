# Create slurm user
useradd slurm

# Configure Slurm
mkdir -p /sc_tools/log/slurm /sc_tools/spool/slurm /sc_tools/spool/slurmd /sc_tools/etc
chown -R slurm:slurm /sc_tools/log/slurm /sc_tools/spool/slurm /sc_tools/spool/slurmd /sc_tools/etc
