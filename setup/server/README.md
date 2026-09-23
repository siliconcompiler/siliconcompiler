# Local sc-server on a real Slurm cluster

A throwaway cluster for testing `-cluster slurm` end to end: `slurmctld`,
`slurmdbd` with a MariaDB accounting store, `slurmrestd`, and a compute node
running `slurmd`.

```sh
docker compose up --build          # first run pulls the base image
curl http://localhost:8080/v1      # the capabilities block
curl http://localhost:8080/v1/healthz
docker compose down -v             # -v also drops the munge key and job files
```

**From a git worktree, build through `./compose.sh` instead** — same arguments,
same result:

```sh
./compose.sh up --build
```

A worktree has no `.git` directory: it has a 64-byte file pointing at one in the
main checkout, which is outside the build context and so unreachable from inside
the container. `setuptools_scm` then fails with a `TypeError` out of
`_version_missing()` that mentions neither git nor the worktree. `compose.sh`
resolves the version on the host with `scversion.sh` and passes it as
`SC_VERSION`, which the Dockerfile uses instead of asking git. A plain
`docker compose build` in a worktree says the same thing in one line rather than
failing obscurely.

The `v1` API is on <http://localhost:8080>, `slurmrestd` on port 6820.

The server runs as `python3 -m siliconcompiler.remote.server` — there is no
`sc-server` console script. It takes three flags:

```sh
python3 -m siliconcompiler.remote.server -port 8080 -datadir /sc_server -cluster slurm
```

Everything else a deployment might say — its nine `limits`, what it advertises
in `features`, any `notices` — has a working default and can be overridden in
`<datadir>/config.json`. Nothing there is required, so a bare `-datadir` starts
a server that serves a complete `GET /v1`.

## Running a real flow through it

The stack carries the EDA tools, so a full ASIC flow works, not just the
scheduler path.

```sh
sc-remote -configure -server http://localhost:8080
cd ../../examples/heartbeat && python3 heartbeat.py -remote
```

`-configure` generates this machine's key, enrols it with the server on first
contact and saves the session. There is no username and no password: under `v1`
the key **is** the credential, and an address that carries a username and a
password has both ignored with a warning saying so.

Where the key and the session are kept:

```sh
python3 -c 'from siliconcompiler import utils; print(utils.default_credentials_file())'
```

The private key sits beside that file as `credentials.key`, both `0600`.

⚠️ There is no default server, so a client that has not been configured says so
twice: *"No remote server address is configured"* when it is asked to do
anything, and the same again from `sc-remote` with the command that fixes it.

When the run ends the client pulls the results back and merges them into its own
build directory, so `project.summary()` works exactly as it does after a local
run. The server keeps its copy under `<datadir>/users/<user>/builds/`, indexed
as artifacts with per-kind retention: manifests and logs for years, bulk outputs
for the deployment's floor.

### Watching, cancelling and reconnecting

A run writes `sc_remote.pkg.json` into its job directory before it uploads
anything, and every command that acts on a job takes that path:

```sh
sc-remote -cfg build/heartbeat/job0/sc_remote.pkg.json              # status
sc-remote -cfg build/heartbeat/job0/sc_remote.pkg.json -reconnect   # re-enter the wait
sc-remote -cfg build/heartbeat/job0/sc_remote.pkg.json -cancel
sc-remote -cfg build/heartbeat/job0/sc_remote.pkg.json -delete
```

Ctrl-C on a running job prints those first two lines with the path filled in.

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

The server is given `-datadir /sc_server` (a named volume) and lays it out
itself:

```
/sc_server/server.db                     the job store
/sc_server/artifacts/<job>/              what a finished run left behind
/sc_server/users/<user>/builds/<job>/    one directory per user per job
/sc_server/users/<user>/cache/           that user's PDKs and data packages
```

Both of the last two matter for a cluster. The job directory is written by the
server and read back by the compute node at the same path, and the **cache has
to be here too**: a compute node need not share a home directory with the
server, and the scheduler hands the server's `cachedir` to the node — so it must
be a path they both see. Without that, every node re-downloads the PDK into its
own `~/.sc/cache`.

They are per user rather than cluster-wide because `ccache` and `coursier`
create their own directories: under one shared tree they land with the first
user's uid and the second user gets `EPERM`, and `chmod` is owner-only, so the
server cannot repair a directory it did not create. The cost is one copy of each
PDK per user rather than one per cluster.

## Credentials

The MariaDB root password is random and discarded; `slurmdbd` connects as an
unprivileged user, and the database port is not published to the host. The one
credential is that user's password, overridable and defaulted for local use:

```sh
SC_SLURM_DB_PASSWORD=... docker compose up --build
```
