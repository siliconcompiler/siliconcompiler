#!/bin/bash

# Set the container's hostname in slurm.conf
sed "s^{{ hostname }}^`hostname`^g" /etc/slurm/slurm.conf.in >  /etc/slurm/slurm.conf

# Start munge and slurm daemons
/etc/init.d/munge start
slurmctld
slurmd
