# Local sc-server on a real Slurm cluster

A throwaway cluster for testing `sc-server -cluster slurm` end to end:
`slurmctld`, `slurmdbd` with a MariaDB accounting store, `slurmrestd`, and a
compute node running `slurmd`.

```sh
docker compose up --build          # first run pulls the base image
curl -X POST http://localhost:8080/check_server/ -d '{}'
docker compose down -v             # -v also drops the munge key and job files
```

`sc-server` is on <http://localhost:8080>, `slurmrestd` on port 6820.

## Running a real flow through it

The stack carries the EDA tools, so a full ASIC flow works, not just the
scheduler path. Submit from your own machine: point a client at the server by
writing its credentials file — the path is `~/.sc/credentials`, **with no
extension**:

```sh
echo '{"address": "localhost", "port": 8080}' > ~/.sc/credentials
python3 -m siliconcompiler.demos.asic_demo -remote
```

If in doubt about where that file belongs, ask siliconcompiler rather than
assuming:

```sh
python3 -c 'from siliconcompiler import utils; print(utils.default_credentials_file())'
```

⚠️ Getting the path wrong is silent: the client falls back to the **public**
server at siliconcompiler.com and your job is uploaded there instead. If the log
says *"Your job will be uploaded to a public server"*, the file is not where the
client looked.

## The base image

Everything the cluster runs comes from `ghcr.io/siliconcompiler/sc_tools`:
slurm, `slurmrestd`, the EDA tools, munge, git, and an Ubuntu 24.04 userland.
The image is public, so no registry credentials are needed. This Dockerfile
adds only siliconcompiler itself — built as a wheel from the working tree, so
the stack tests the code you are sitting on rather than a release.

`sc_tools` rather than `sc_runner`: the two are the same except that
`sc_runner` also pip-installs a released siliconcompiler, which this image
would immediately overwrite. (`sc_slurm` is the one image here that is *not*
public, a separate reason not to depend on it.)

Pick the image with `SC_TOOLS_IMAGE`, without editing anything:

```sh
SC_TOOLS_IMAGE=ghcr.io/siliconcompiler/sc_tools:<tag> docker compose up --build
```

⚠️ It must be an image whose slurm matches the version pinned in `_tools.json`
and which has `slurmrestd` built in — `entrypoint.sh` starts it. An image
predating the slurm bump comes up with the wrong version and no REST daemon.

Daily CI builds this stack on the image its `docker_image` job resolves, and
submits both the ASIC and FPGA demos through it, checking that a GDS and a
bitstream come back to the client (`remote_server` in `daily_ci.yml`).

Nothing outside the repo is referenced at runtime: a public base image, one
local build, and named volumes for all shared state. No host paths are bind
mounted.

## Adding compute nodes

```sh
docker compose up -d --scale scrunner=4     # or any N
```

That is the whole of it — no config change, and the running services are not
restarted. The runners **register themselves**: each starts `slurmd -Z`
(Slurm's dynamic nodes), and the controller records the address and hostname it
registers with, so nothing has to know their names in advance. `slurm.conf` has
no `NodeName` lines at all; `PartitionName=sc Nodes=ALL` is what admits a node
the moment it appears.

Scaling down works too — a runner runs `scontrol delete nodename=$(hostname)`
on the way out, so the controller is not left holding nodes that will never
answer.

Two settings in `slurm.conf` make this possible, and dynamic nodes will not
work without them: `SelectType=select/cons_tres` (the only select plugin that
supports them) and `MaxNodeCount`, the ceiling on how many may register.

Node names are container IDs, since that is what a scaled replica's hostname
is. `sinfo -N -l` lists them.

## Things that are less obvious than they look

- **The munge key lives in a volume, not the image.** Any repo edit invalidates
  the wheel layer and everything after it, so a baked key would change on every
  rebuild — and rebuilding one service would leave it unable to authenticate to
  the others (`Munge decode failed: Invalid credential`).
- **`slurmd` runs as a child of PID 1, deliberately.** cgroup/v2 derives the
  cgroup root by reading `/proc/1/cgroup` and stripping the last component,
  expecting PID 1 to be in `init.scope`. If `slurmd` *is* PID 1 it moves itself
  into `system.slice/slurmstepd.scope/slurmd`, and `slurmstepd` then looks for
  the slice a second level down and dies on the doubled path.
- **Only the runner gets extra privilege**, and only for `slurmd`'s cgroup
  setup: `CAP_SYS_ADMIN` to remount its own `/sys/fs/cgroup` read-write, plus
  AppArmor unconfined, because the profile — not the capability — is what
  refuses that remount. The tasks slurm runs need nothing special.
- **`slurmrestd` does not get that privilege.** It unshares the System V IPC
  and file-descriptor namespaces on startup, which would need `CAP_SYS_ADMIN`,
  so `SLURMRESTD_SECURITY=disable_unshare_sysv,disable_unshare_files` turns
  those off instead. It still refuses to run as root or `SlurmUser`, and still
  runs under its own unprivileged account.
- **Recreating `scserver` alone can leave the node unregistered** (`sinfo`
  shows `unk*`). Restart the runner, or bring the stack up together.

## What the shared mount looks like

`sc-server` is given `-nfsmount /sc_server` (a named volume) and lays it out
itself:

```
/sc_server/builds/<jobhash>/   one directory per job
/sc_server/cache/              downloaded PDKs and data packages
```

Both matter for a cluster. The job directory is written by the server and read
back by the compute node at the same path, and the **cache has to be here too**:
a compute node need not share a home directory with the server, and the
scheduler hands the server's `cachedir` to the node — so it must be a path they
both see. Without that, every node re-downloads the PDK into its own
`~/.sc/cache`.

## Credentials

The MariaDB root password is random and discarded; `slurmdbd` connects as an
unprivileged user, and the database port is not published to the host. The one
credential is that user's password, overridable and defaulted for local use:

```sh
SC_SLURM_DB_PASSWORD=... docker compose up --build
```
