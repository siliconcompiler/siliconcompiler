Setting Up a Minimal Local Slurm Cluster
========================================

The SiliconCompiler project is capable of deferring individual job steps to hosts in a high-performance computing cluster. Currently, only the `Slurm job scheduler <https://slurm.schedmd.com/overview.html>`_ is supported.

In order to use this functionality, you will need access to a Slurm cluster. Configuring a performant HPC cluster is outside the scope of this document, but this chapter will walk you through the process of configuring your local machine as a "cluster" consisting of a single host. It will also describe how to test the Slurm functionality, and how to add new hosts to a cluster.

This chapter will use Ubuntu 20.04 as a target OS, but the process should be very similar for other UNIX-like systems.

Initial Slurm Configuration
---------------------------

User and Group Configuration
++++++++++++++++++++++++++++

Before installing the Slurm software, you should create users and groups named `slurm` and `munge`::

    groupadd slurm
    groupadd munge
    useradd slurm -g slurm
    useradd munge -g munge

It is **VERY IMPORTANT** that these users and groups have the same UIDs and GIDs on every host in the cluster. Our test "cluster" will only have a single host, but if you want to set up a real cluster later, you can create these groups and users with specific IDs::

    groupadd slurm -g <slurm_gid>
    groupadd munge -g <munge_gid>
    useradd slurm -u <slurm_uid> -g <slurm_gid>
    useradd munge -u <munge_uid> -g <munge_gid>

You can find existing user and group IDs in the `/etc/passwd` file, or by using the `id` and `getent` commands::

    id -u <username>
    getent group <groupname>

Note that changing a user or group's ID after it already exists can cause issues, because filesystem permissions are usually not updated to match the new IDs.

Slurm Daemon Installation
+++++++++++++++++++++++++

The core Slurm scheduling logic is contained in two daemons:

- `slurmctld`: The "Slurm control daemon" runs on a "control node". This daemon manages the "compute nodes" in a cluster and delegates jobs to them.

- `slurmd`: The "Slurm daemon" runs on "compute nodes". This daemon listens for new commands from the "control node", and executes jobs which are sent to the host that it is running on.

Because we are setting up a test cluster on a single host, we will run both deamons on the same machine.

The slurm daemons, and a supporting `slurm-client` package, should be available in the package managers of common Linux distributions. In Ubuntu, you can install them with::

    apt-get install slurmctld slurmd slurm-client

Slurm also relies on `munge` to encrypt communications between hosts. It should be installed as a dependency of the Slurm packages, but if not::

    apt-get install munge

Munge will create a default key when it is installed at `/etc/munge/munge.key`. This key must be identical on every host in the cluster, so if you set up a cluster with multiple hosts, you will need to copy this file onto every host in the cluster. You can re-generate a new munge key with::

    sudo create-munge-key

Slurm Configuration Files
+++++++++++++++++++++++++

A minimal Slurm cluster requires three basic configuration files:

- `/etc/slurm-llnl/cgroup.conf`: A "control group" configuration file. This describes which resources Slurm is allowed to access, and how Slurm should manage system resources.

- `/etc/slurm-llnl/cgroup_allowed_devices.conf`: A list of filesystem paths to devices which Slurm should be able to access. The name and location of this file is arbitrary; it will be referenced in the `cgroup.conf` file.

- `/etc/slurm-llnl/slurm.conf`: The core cluster configuration file. This describes which hosts should be included in a cluster, what those hosts' capabilities and roles are. It can also include config variables for various cluster behaviors.

Most of the contents of the example files presented here come from the Slurm project's documentation. You may need to extend or modify them if you create a more complex cluster with more hosts or system resources.

cgroup.conf
***********

A minimal `/etc/slurm-llnl/cgroup.conf` file is fairly brief::

    CgroupMountpoint="/sys/fs/cgroup"
    CgroupAutomount=yes
    CgroupReleaseAgentDir="/etc/slurm-llnl/cgroup"
    AllowedDevicesFile="/etc/slurm-llnl/cgroup_allowed_devices.conf"
    ConstrainCores=no
    TaskAffinity=no
    ConstrainRAMSpace=yes
    ConstrainSwapSpace=no
    ConstrainDevices=no
    AllowedRamSpace=100
    AllowedSwapSpace=0
    MaxRAMPercent=100
    MaxSwapPercent=100
    MinRAMSpace=30

If your Linux installation places its control group devices in a different directory from `/sys/fs/cgroup`, you may need to modify that parameter.

The `AllowedDevicesFile` parameter refers to the `cgroup_allowed_devices.conf` file which we will create in the next section.

You can read more about `cgroup.conf` parameters `in the Slurm documentation <https://slurm.schedmd.com/cgroup.conf.html>`_.

cgroup_allowed_devices.conf
***************************

The list of cgroup devices which Slurm should be allowed to access is typically quite short. This file path should match the value of `AllowedDevicesFile` in your `etc/slurm-llnl/cgroup.conf` file::

    /dev/null
    /dev/urandom
    /dev/zero
    /dev/sda*
    /dev/cpu/*/*
    /dev/pts/*

If your system has other core resources that the cluster may need to access, you can add those device paths here.

slurm.conf
**********

The most reliable way of setting up a comprehensive `slurm.conf` file is by using Slurm's "configurator" web tool, but the large number of fields can be confusing if you are new to Slurm.

If you want to use the "configurator" tool, it is available online on the Slurm website in a `"normal" <https://slurm.schedmd.com/configurator.html>`_ and `"easy" <https://slurm.schedmd.com/configurator.html>`_ version. It is a simple HTML page, though, so you can also run it locally by installing the Slurm documentation package::

    apt-get install slurm-wlm-doc

The "configurator" pages will then be installed on your local machine, and you will be able to open them in a web browser. The default file paths in Ubuntu are::

    /usr/share/doc/slurm-wlm/html/configurator.html
    /usr/share/doc/slurm-wlm/html/configurator.easy.html

For our minimal single-host test cluster, you can skip the "configurator" and use this as a template::

    # slurm.conf file.
    # Put this file on all nodes of your cluster.
    # See the slurm.conf man page for more information.
    SlurmctldHost=<your_hostname>
    
    MpiDefault=none
    ProctrackType=proctrack/cgroup
    ReturnToService=1
    SlurmctldPidFile=/run/slurmctld.pid
    SlurmdPidFile=/run/slurmd.pid
    SlurmdSpoolDir=/var/spool/slurmd
    SlurmUser=slurm
    StateSaveLocation=/var/spool/slurm
    SwitchType=switch/none
    TaskPlugin=task/cgroup
    #SrunPortRange=<start_port>-<end_port>
    
    # SCHEDULING
    SchedulerType=sched/backfill
    SelectType=select/linear
    
    # LOGGING AND ACCOUNTING
    AccountingStorageType=accounting_storage/none
    ClusterName=<cluster_name>
    
    JobAcctGatherType=jobacct_gather/none
    SlurmctldLogFile=/var/log/slurm-llnl/log.log
    SlurmdLogFile=/var/log/slurm-llnl/dlog.log
    
    # COMPUTE NODES
    NodeName=<your_hostname> NodeAddr=<your_dns> Features=SHARED <host_info>
    PartitionName=debug Nodes=<your_hostname> Default=YES MaxTime=INFINITE State=U

Note the `Features=SHARED` parameter in the compute node definition. Slurm allows you to define attributes to restrict which compute nodes are allowed to run which jobs. The SiliconCompiler project uses `SHARED` as a catch-all feature when more complex job delegation is not required.

The `<your_hostname>` values should be set to the output of the `hostname` command, and the `<your_dns>` value should be set to a value which DNS services will resolve to your host. Cloud providers will typically provide a public DNS for virtual hosts, but you can use `localhost` for a test cluster on your local machine.

The `<host_info>` values define the capabilities of a compute node; number of CPUs, available RAM, etc. You can get these values for a host by running `slurmd -C`, and copying the output from `CPUs=[...]` through `RealMemory=[...]`. You may want to reduce the `RealMemory` value a bit, because Slurm will take nodes out of service if their available RAM falls below that threshold.

The `SrunPortRange` value is commented out here, but you can use it to limit the range of ports which Slurm is allowed to use for "phoning home" from compute nodes to the control node. If you want to avoid using reserved ports or set up a firewall rule with more restrictive port ranges than 0-65535, you can set your desired port range with this parameter.

The `ClusterName` parameter is arbitrary. I like to name clusters after roads, but things like mountains, forests, mythical figures, etc. are also good choices. Slurm's documentation recommends using lowercase characters in the name. It looks like this parameter is mostly used for accounting in Slurm's optional database extension, so it should not be too important in a minimal test cluster.

**Important note**: Every host in your cluster should use an identical `slurm.conf` file. If you eventually set up a cluster with shared networked storage, you can easily propagate changes to `slurm.conf` by placing the file in shared storage, and making each host's `/etc/slurm-llnl/slurm.conf` file a symbolic link to `<shared_storage>/slurm.conf`.

Slurm Startup
+++++++++++++

To start your slurm cluster, all you need to do is restart the `slurmctld` and `slurmd` daemons. These daemons should be restarted on all hosts in the cluster whenever you make changes to configuration files like `slurm.conf`::

    sudo service restart slurmctld
    sudo service restart slurmd

Once the daemons are running with the correct config files loaded, you should be able to issue commands to the cluster using `srun`::

    srun hostname

Running SiliconCompiler on a Cluster
++++++++++++++++++++++++++++++++++++

To run a SiliconCompiler job on your cluster, all you need to do is set the `jobscheduler` schema parameter to `slurm`. If you are using the Python API::

    chip.set('jobscheduler', 'slurm')

If you are running a job from the command-line, simply add `-jobscheduler slurm` to the command.

There are a few restrictions to be aware of if you decide to set up a more complex cluster:

* Clustered jobs must be run from a host which is acting as the "control node" for a Slurm cluster.

* The build directory must be placed in a location which is accessible to all hosts in the cluster. If you have multiple hosts in your cluster, they will need to share a networked storage drive using a protocol such as NFS.

Troubleshooting
+++++++++++++++

**TODO**
