#!/bin/bash

# Set the container's hostname in slurm.conf
sed "s^{{ hostname }}^`hostname`^g" /sc_tools/slurm_cfg/slurm.conf.in > /sc_tools/etc/slurm.conf

# Start munge and slurm daemons
/etc/init.d/munge start
slurmctld
slurmd
