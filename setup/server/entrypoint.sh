#!/bin/bash
#
# One image, three roles. Usage: entrypoint.sh <dbd|ctld|node>
#
# Each role starts munge first -- every slurm daemon authenticates with it --
# and then runs its own daemon in the foreground so that docker sees the logs
# and can stop the container.

set -euo pipefail

role="${1:?usage: entrypoint.sh <dbd|ctld|node>}"

start_munge() {
    # Every slurm daemon authenticates with the same munge key, so it lives in
    # a volume shared by all of them. Whoever starts first creates it; the lock
    # directory makes that atomic, so two containers starting together cannot
    # write two different keys.
    if [ ! -s /etc/munge/munge.key ]; then
        if mkdir /etc/munge/.keylock 2>/dev/null; then
            dd if=/dev/urandom of=/etc/munge/munge.key.new bs=1024 count=1 status=none
            chown munge:munge /etc/munge/munge.key.new
            chmod 400 /etc/munge/munge.key.new
            mv /etc/munge/munge.key.new /etc/munge/munge.key
            rmdir /etc/munge/.keylock
            echo "created a shared munge key"
        else
            for _ in $(seq 1 60); do
                [ -s /etc/munge/munge.key ] && break
                sleep 0.5
            done
        fi
    fi
    if [ ! -s /etc/munge/munge.key ]; then
        echo "no munge key appeared in /etc/munge" >&2
        exit 1
    fi

    # munged will not use a key it does not own, and refuses to start on a
    # stale socket left by a previous container.
    chown -R munge:munge /etc/munge /var/log/munge /var/lib/munge 2>/dev/null || true
    mkdir -p /run/munge && chown munge:munge /run/munge
    runuser -u munge -- /usr/sbin/munged --force

    for _ in $(seq 1 30); do
        [ -S /run/munge/munge.socket.2 ] && return 0
        sleep 0.5
    done
    echo "munged did not come up" >&2
    exit 1
}

prepare_cgroups() {
    # cgroup v2 has a "no internal processes" rule: a cgroup cannot both hold
    # processes and enable controllers for its children. Docker leaves this
    # container's processes in the root of its cgroup namespace, which is a
    # normal cgroup rather than the real root, so the rule applies and slurmd's
    # attempt to enable cpu/cpuset/memory there fails with EOPNOTSUPP.
    #
    # Move them into a leaf first. This is exactly what systemd does with
    # init.scope on a real host, and everything forked from here inherits it,
    # so the root stays empty.
    mkdir -p /sys/fs/cgroup/init.scope
    while read -r pid; do
        echo "$pid" > /sys/fs/cgroup/init.scope/cgroup.procs 2>/dev/null || true
    done < /sys/fs/cgroup/cgroup.procs

    # With the root empty, delegate the controllers slurmd wants down to the
    # slice its stepd scope lives in. cgroup_v2.c hardcodes system.slice
    # (SYSTEM_CGSLICE) and creates only the leaf scope under it.
    echo "+cpuset +cpu +memory" > /sys/fs/cgroup/cgroup.subtree_control
    mkdir -p /sys/fs/cgroup/system.slice
    echo "+cpuset +cpu +memory" > /sys/fs/cgroup/system.slice/cgroup.subtree_control

    echo "cgroup v2 ready: $(cat /sys/fs/cgroup/system.slice/cgroup.controllers)"
}

wait_for_port() {
    local host="$1" port="$2" name="$3"
    for _ in $(seq 1 120); do
        if (echo > "/dev/tcp/${host}/${port}") 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    echo "timed out waiting for ${name} at ${host}:${port}" >&2
    exit 1
}

case "$role" in
dbd)
    # slurmdbd.conf carries the database password, so it is written here from
    # the environment rather than baked into the image, and slurmdbd requires
    # it to be unreadable by anyone else.
    cat > /sc_tools/etc/slurmdbd.conf <<CONF
DbdHost=slurmdbd
SlurmUser=slurm
StorageType=accounting_storage/mysql
StorageHost=slurmdb
StorageUser=slurm
StoragePass=${SC_SLURM_DB_PASSWORD:?SC_SLURM_DB_PASSWORD must be set}
StorageLoc=slurm_acct_db
CONF
    chown slurm:slurm /sc_tools/etc/slurmdbd.conf
    chmod 600 /sc_tools/etc/slurmdbd.conf

    start_munge
    wait_for_port slurmdb 3306 "mariadb"
    exec slurmdbd -D
    ;;

ctld)
    start_munge
    wait_for_port slurmdbd 6819 "slurmdbd"

    # The JWT signing key for slurmrestd. Generated per container rather than
    # baked in, and only slurmctld ever reads it -- slurmrestd forwards the
    # caller's token instead of verifying it itself.
    key=/sc_tools/spool/slurm/jwt_hs256.key
    if [ ! -f "$key" ]; then
        dd if=/dev/urandom of="$key" bs=32 count=1 status=none
        chown slurm:slurm "$key"
        chmod 600 "$key"
    fi

    slurmctld -D &

    # Wait for the controller before anything asks it a question.
    wait_for_port scserver 6817 "slurmctld"

    # The REST API, if this image has it. Nothing calls it yet; it runs so the
    # endpoint is reachable and so a broken build shows up here.
    if command -v slurmrestd >/dev/null 2>&1; then
        # SLURMRESTD_SECURITY turns off two things slurmrestd does to itself at
        # startup: unshare(CLONE_SYSVSEM) and unshare(CLONE_FILES), which detach it
        # from the System V semaphore adjustments and the file-descriptor table it
        # inherited from its parent. Docker's default seccomp profile refuses
        # unshare without CAP_SYS_ADMIN, so without this the daemon exits with
        # "Unable to unshare System V namespace: Operation not permitted".
        #
        # It is the narrowest of the three ways out. The alternatives --
        # seccomp=unconfined or CAP_SYS_ADMIN, both verified to work -- weaken the
        # whole container's sandbox to keep two hardening steps inside one daemon,
        # whose parent here is an entrypoint shell with nothing to isolate from.
        #
        # Note what is NOT set: disable_user_check, the dangerous member of this
        # family, which slurmrestd itself refuses on release builds ("will allow
        # anyone to run any command on the cluster as root"). Authentication,
        # authorization and the account the daemon runs under are unchanged -- it
        # still refuses to run as root or as SlurmUser.
        SLURMRESTD_SECURITY=disable_unshare_sysv,disable_unshare_files \
            runuser -u slurmrestd -- slurmrestd 0.0.0.0:6820 &
    else
        echo "NOTE: slurmrestd was not built into this image" >&2
    fi

    # Point a client run *inside this container* at this server rather than at
    # the public default, so `python3 -m siliconcompiler.demos.asic_demo
    # -remote` works out of the box here. Harmless to the runners, which share
    # this volume but are not clients.
    #
    # The path is asked of siliconcompiler rather than assumed: it is
    # "~/.sc/credentials", with no extension, which is easy to get wrong -- and
    # getting it wrong is silent, the client just uses the public default
    # server instead.
    creds=$(python3 -c 'from siliconcompiler import utils; print(utils.default_credentials_file())')
    mkdir -p "$(dirname "$creds")"
    if [ ! -f "$creds" ]; then
        printf '{"address": "localhost", "port": 8080}\n' > "$creds"
        echo "wrote client credentials to $creds"
    fi

    # sc-server creates builds/ and cache/ under the mount itself.
    mkdir -p /sc_server
    cd /sc_server
    exec sc-server \
        -cluster slurm \
        -port 8080 \
        -nfsmount /sc_server \
        -checkinterval 5
    ;;

node)
    # slurmd builds its own cgroup hierarchy, because cgroup.conf sets
    # IgnoreSystemd=yes and there is no systemd here to ask over DBus. Two
    # things have to be true for that to work, and neither is by default:
    #
    #   1. /sys/fs/cgroup must be writable. Docker mounts the container's own
    #      cgroup namespace there read-only, so it is remounted below --
    #      which needs CAP_SYS_ADMIN *and* AppArmor out of the way, since the
    #      profile is what refuses it on Ubuntu.
    #   2. the hierarchy must be prepared the way systemd would prepare it:
    #      an empty root, delegated controllers, and a system.slice to put the
    #      stepd scope in. See prepare_cgroups above.
    if [ ! -w /sys/fs/cgroup ]; then
        mount -o remount,rw /sys/fs/cgroup 2>/dev/null || true
    fi
    if [ ! -w /sys/fs/cgroup ]; then
        echo "ERROR: /sys/fs/cgroup is read-only and could not be remounted." >&2
        echo "slurmd cannot set up cgroup/v2 without it. The scrunner service" >&2
        echo "needs cap_add: SYS_ADMIN and security_opt: apparmor=unconfined" >&2
        echo "(see docker-compose.yml)." >&2
        exit 1
    fi
    prepare_cgroups

    start_munge
    wait_for_port scserver 6817 "slurmctld"

    # slurmd registers itself with the controller (-Z) instead of being named
    # in slurm.conf, so scaling this service needs no configuration anywhere:
    # the controller records the NodeAddr and NodeHostname it registers with.
    # RealMemory is passed explicitly and kept low -- a node is marked invalid
    # when it claims more memory than it has, never when it claims less.
    #
    # slurmd deliberately runs as a CHILD, not via exec.
    #
    # cgroup/v2 derives the cgroup root by reading /proc/1/cgroup and stripping
    # the last component (_get_init_cg_path in cgroup_v2.c), because it expects
    # PID 1 to sit in init.scope. If slurmd is PID 1 it moves itself into
    # system.slice/slurmstepd.scope/slurmd, and that derivation then yields
    # ".../slurmstepd.scope" as the root -- so slurmstepd looks for
    # system.slice/slurmstepd.scope *under* it and dies on the doubled path:
    #
    #   error: cannot read /sys/fs/cgroup/system.slice/slurmstepd.scope/
    #          system.slice/slurmstepd.scope/cgroup.controllers
    #   fatal: Couldn't load all plugins
    #
    # Keeping this shell as PID 1 in init.scope leaves /proc/1/cgroup at
    # "/init.scope", which strips to the real root.
    slurmd -D -Z --conf "RealMemory=500" &
    slurmd_pid=$!

    # On the way out, take the node back out of the cluster, so scaling down
    # does not leave the controller holding nodes that will never answer.
    cleanup() {
        scontrol delete nodename="$(hostname)" 2>/dev/null || true
        kill -TERM "$slurmd_pid" 2>/dev/null || true
    }
    trap cleanup INT TERM
    wait "$slurmd_pid"
    ;;

*)
    echo "unknown role: $role (expected dbd, ctld or node)" >&2
    exit 1
    ;;
esac
