#!/bin/bash
#
# One image, four roles. Usage: entrypoint.sh <bootstrap|dbd|ctld|node>
#
# Each role starts munge first -- every slurm daemon authenticates with it --
# and then runs its own daemon in the foreground so that docker sees the logs
# and can stop the container.

set -euo pipefail

role="${1:?usage: entrypoint.sh <bootstrap|dbd|ctld|node>}"

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
bootstrap)
    # 🔴 The one role that is not a daemon and does not touch munge or slurm.
    # It puts the two images compose just built into the registry, registers
    # them and stages their bundles, and then exits -- and `scserver` waits for
    # that exit, which is what makes `docker compose up` the whole procedure.
    # See bootstrap.py for why it is a service and not a script.
    exec /usr/local/bin/sc-bootstrap
    ;;

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

    # 🔴 **Recover the JOBS and never the NODES.** StateSaveLocation is on a
    # volume so a controller restart does not forget what was queued -- but
    # every node in this cluster is DYNAMIC: it exists because `slurmd -Z` said
    # so, and it appears in no configuration file. Recovering one from state
    # asserts a node exists when nothing has said so since the restart, and if
    # that container is gone the controller cheerfully schedules onto a ghost.
    #
    # What that looks like, and it is not subtle:
    #
    #   sinfo               6 nodes, for 2 replicas
    #   slurmctld: error: Batch completion for JobId=41 sent from wrong node
    #              (1bfa50e484ec rather than 9b6a4c6c8cb0). Was the job
    #              requeued due to node failure?
    #
    # -- real jobs failing against a node that no longer exists. A dynamic
    # node's existence is the node's to assert, so this drops the controller's
    # memory of it and lets the live ones re-register, which they do within
    # seconds. `job_state` is deliberately left alone.
    rm -f /sc_tools/spool/slurm/node_state /sc_tools/spool/slurm/node_state.old

    # Nothing to do for StateSaveLocation. It is slurm-owned in the image --
    # install-slurm.sh does it for the base, the server stage does it for the
    # slim one -- and docker pre-populates an empty NAMED volume from the image
    # path, ownership included. Verified: the volume comes up 999:996.
    #
    # ⚠️ That copy is a named-volume behaviour only. Bind-mount a host
    # directory over it instead and it arrives root-owned, and slurmctld
    # refuses a state directory it cannot write.

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
    ctld_pid=$!

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
        restd_pid=$!
    else
        echo "NOTE: slurmrestd was not built into this image" >&2
    fi

    # No client credential is seeded here. Under the v1 API a client holds a
    # DPoP key pair rather than an address and a password, so the file this
    # used to write has no meaning until the client that mints one exists.
    # It comes back with that client.

    # The server lays out <datadir> itself: the store, the artifacts, and one
    # tree per user for builds and caches.
    mkdir -p /sc_server
    cd /sc_server

    # config.json is written by the `bootstrap` role, which runs to completion
    # before this one is started -- see bootstrap.py, which also says what each
    # of the mounts in it is for. One writer, deliberately: two places seeding
    # the same policy file is how a mount list and the bundles staged against
    # it drift apart.

    python3 -m siliconcompiler.remote.server \
        -cluster slurm \
        -port 8080 \
        -datadir /sc_server &
    server_pid=$!

    # Supervise rather than exec, so this shell stays PID 1 and all three
    # daemons are watched. Under an "exec" of the server the container reports
    # healthy for as long as that process lives, even with slurmctld dead
    # underneath it -- which surfaces later and far away, as jobs that never
    # dispatch. Exiting on the first child to die makes the container's status
    # say what actually happened.
    # 🔴 Signal them AND WAIT. slurmctld saves its state on SIGTERM by writing
    # job_state.new, fsyncing and renaming it into place -- so a shell that
    # signals and then exits takes PID 1 down mid-save, docker tears the
    # container apart, and what is left on the volume is a ZERO-LENGTH
    # job_state.new and no job_state at all. The next start then says
    #
    #   error: Could not open job state file .../job_state
    #   error: NOTE: Trying backup state save file. Jobs may be lost!
    #
    # which is indistinguishable from never having saved, and was happening on
    # every restart. Putting StateSaveLocation on a volume is necessary and was
    # not sufficient: without this the volume just collects the half-written
    # file.
    shutdown() {
        kill -TERM $ctld_pid ${restd_pid:-} $server_pid 2>/dev/null || true

        # Bounded: compose's stop_grace_period is what is actually enforced,
        # and a controller that will not go in ten seconds is not going to.
        for _ in $(seq 1 100); do
            kill -0 $ctld_pid 2>/dev/null || return 0
            sleep 0.1
        done
        echo "slurmctld did not stop in 10s; its state may be incomplete" >&2
    }
    trap 'shutdown; exit 0' INT TERM

    wait -n
    status=$?
    echo "a daemon exited (status $status); shutting the container down" >&2
    shutdown
    exit "$status"
    ;;

node)
    # Where crun keeps container state, named explicitly in oci.conf. Created
    # here because crun will not make its own root directory.
    mkdir -p /run/crun

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
    start_slurmd() {
        slurmd -D -Z --conf "RealMemory=500" &
        slurmd_pid=$!
    }
    start_slurmd

    # On the way out, take the node back out of the cluster, so scaling down
    # does not leave the controller holding nodes that will never answer.
    #
    # 🔴 **And then EXIT, rather than returning into the loop below.** A trap
    # interrupts the `sleep`, runs, and hands control back -- so without this
    # the shell went round again, slept another fifteen seconds, and was still
    # sleeping when docker's ten-second grace period ran out. Every stop became
    # a SIGKILL (exit 137), and `scontrol delete` raced it: the stale nodes
    # that accumulate in `sinfo` after a rebuild are that race, not slurm.
    cleanup() {
        scontrol delete nodename="$(hostname)" 2>/dev/null || true
        kill -TERM "$slurmd_pid" 2>/dev/null || true

        for _ in $(seq 1 50); do
            kill -0 "$slurmd_pid" 2>/dev/null || break
            sleep 0.1
        done
        exit 0
    }
    trap cleanup INT TERM

    # 🔴 Deleting the node is not politeness, it is what stops a zombie job.
    # A dynamic node that vanishes without being deleted leaves the controller
    # holding it AND whatever was running on it, reported RUNNING for ever on a
    # container that no longer exists -- and the API believes the scheduler,
    # so the job never leaves `running` either.

    # 🔴 **Re-register when the controller has forgotten us.** A dynamic node
    # exists only in slurmctld's memory -- "slurmd -Z" tells the controller it
    # is here and appears in no configuration file -- so a controller that
    # restarts comes back with no record of any of them. `sinfo` then reports
    #
    #   compute*  up  infinite  0  n/a
    #
    # and every job sits at PENDING (PartitionConfig) for ever. Nothing about
    # that says "restart the runners", which is the fix, and it had to be done
    # by hand in the right order every time the server was rebuilt.
    #
    # ⚠️ Restarting slurmd ends whatever it was running, and that is not a
    # cost: a controller with no record of this node has already lost those
    # jobs. The node is unreachable work either way, and this way it comes
    # back.
    #
    # The check is deliberately two conditions. The controller being
    # unreachable is a different thing -- it is down, or restarting -- and
    # bouncing slurmd at it then would just churn until it returns.
    #
    # ⚠️ The interval is also how long a stop can take, which is why `cleanup`
    # exits rather than waiting for the next tick.
    while true; do
        if ! kill -0 "$slurmd_pid" 2>/dev/null; then
            wait "$slurmd_pid"
            status=$?
            echo "slurmd exited (status $status)" >&2
            exit "$status"
        fi

        # 🔴 Backgrounded and waited on, NOT a plain `sleep 15`. Bash defers a
        # trap until the current FOREGROUND command finishes, so with a plain
        # sleep the TERM handler did not run for up to fifteen seconds --
        # longer than docker's ten-second grace period, so every stop became a
        # SIGKILL (exit 137) and `scontrol delete` never ran. That is where the
        # stale nodes in `sinfo` came from, and the jobs stuck RUNNING on a
        # container that no longer exists. `wait` is interruptible; `sleep` is
        # not. Measured: 14s to die versus 0s.
        sleep 15 &
        wait $! 2>/dev/null || true

        if scontrol ping >/dev/null 2>&1 &&
           ! scontrol show node "$(hostname)" >/dev/null 2>&1; then
            echo "the controller has no record of this node; re-registering" >&2
            kill -TERM "$slurmd_pid" 2>/dev/null || true
            wait "$slurmd_pid" 2>/dev/null || true
            start_slurmd
        fi
    done
    ;;

*)
    echo "unknown role: $role (expected bootstrap, dbd, ctld or node)" >&2
    exit 1
    ;;
esac
