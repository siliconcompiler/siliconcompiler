# Local sc-server on a real Slurm cluster

A throwaway cluster for testing `-cluster slurm` end to end: `slurmctld`,
`slurmdbd` with a MariaDB accounting store, `slurmrestd`, and a compute node
running `slurmd`.

```sh
docker compose up                  # that is the whole procedure
curl http://localhost:8080/v1      # the capabilities block
curl http://localhost:8080/v1/healthz
docker compose up --build          # after you change the source
docker compose down -v             # -v also drops the munge key and job files
```

🔴 **There is no second command and no order to get right.** A one-shot
`bootstrap` service pushes the images compose just built into this stack's
registry, registers them, stages their bundles and writes `config.json`, and
`scserver` does not start until it has exited 0. It used to be `compose.sh up
--build` followed by `publish.sh` with a restart ordering that bit whenever it
was forgotten — and, worse, a deadlock: a deployment set to run jobs in
containers with an empty registry refuses to start, so resetting the store left
a server that would not come up and a registration tool that needed it running.

⚠️ **`bootstrap` is the one thing in this stack with the docker socket**, for
as long as it runs and for exactly two calls. The images have to get from the
daemon that just built them into the registry, and the daemon is the only thing
that knows their layers. Nothing else can see it — the compute nodes
deliberately cannot, because they run containers through `crun`, which is a
binary Slurm execs.

**A git worktree needs nothing special.** A worktree has no `.git` directory —
it has a 64-byte file pointing at one in the main checkout, outside the build
context — so the build reads the version from `siliconcompiler/_version.py`,
which an editable install has already written. `SC_VERSION=...` overrides both.

🔴 **The version it uses is the last TAG, and that matters.**
`siliconcompiler.__version__` is `__base_version__`, which stays at the tag for
every commit after it, so a checkout 42 commits past `v0.38.9` reports `0.38.9`
and the image has to as well. Deriving `0.38.10.dev42` made the server
advertise a version the very checkout that built it never sends: every submit
from that machine came back `version-skew`, *install a version this server
accepts*, and there was none to install.

## Three images, and which one runs where

| | |
|---|---|
| `sc-server` | slurmctld, slurmdbd, slurmrestd and the API — **~0.7 GB**, no EDA tools |
| `sc-runtime` | SiliconCompiler and the Slurm client — **~0.6 GB**, the framework image |
| `sc-server-slurm` | the compute node, and what a node's task runs inside — **~6.5 GB** |

All three come out of one `Dockerfile` as three `target:`s, so they share a
build graph and a layer cache. A controller is not an EDA machine: it
schedules, answers HTTP and unpacks bundles.

⚠️ **What the split saves, said plainly.** It does not remove a build — the big
image still has to exist, because it is what a node's task runs inside — and it
frees no disk while `scrunner` runs it, since docker shares the layers. What it
buys is a server container of a few hundred megabytes rather than seven
gigabytes, a much faster rebuild when only SiliconCompiler changed, and a
controller whose image contains nothing it could accidentally run.

The `v1` API is on <http://localhost:8080>, `slurmrestd` on port 6820.

The server runs as `python3 -m siliconcompiler.remote.server` — there is no
`sc-server` console script. It takes three flags:

```sh
python3 -m siliconcompiler.remote.server -port 8080 -datadir /sc_server -cluster slurm
```

Everything else a deployment might say — its `limits`, what it advertises
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

## The portal

```sh
sc-remote -portal
```

Six screens over the same decisions the API makes: jobs and their nodes, logs
live or archived, artifacts, devices, account, and the image registry. It is
where the two columns nothing publishes on the wire are read &mdash; which image
a node ran in, and which Slurm job it became.

🔴 **Every authorization decision goes through the code the API handlers call.**
The portal does not call its own API over HTTP &mdash; a browser holds no device
key &mdash; so it reads through the shared layer instead, and every link it
hands the browser for bytes is a *signed* storage URL whose signature is the
whole credential.

Browser sessions live in the server process and in no table, so restarting it
signs everyone out. Running `sc-remote -portal` again is the whole recovery.

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

## The image registry, and running a job inside one

A server can run every job inside a container it has registered, resolving one
image per node from what the job says it needs. **Slurm places those
containers** — `srun --container <bundle>`, inside the one allocation the job
already has — rather than SiliconCompiler's docker scheduler, because
`option,scheduler,name` holds a single value and a node handed to docker is a
node Slurm never sees. It also keeps `option,scheduler,queue` meaning what it
means on a cluster, which is the partition.

Each node becomes **its own Slurm job**, not a step inside the batch job. That
is not a preference — measured on this stack:

```
batch       job=5 partition=sc
plain-step  job=5 step=0
srun --partition=sc ...   -> job=5 step=1   # the partition is SILENTLY IGNORED
SLURM_JOB_ID unset, same  -> job=6 step=0   # its own job
```

A step shares the batch job's allocation and its `--partition` does nothing, so
the runner clears `SLURM_JOB_ID` and every node is scheduled on its own terms.
That is also what lets the batch job itself sit in a small partition: it
coordinates and computes nothing.

### What happens to a node job when the run goes away

Each node is a Slurm job of its own, and the server writes its id into
`job_nodes.scheduler_job_id` — so *which Slurm job was that* stays answerable
after the fact, which is the question that reaches a support thread.

🔴 **It is also what makes a cancel real.** Cancelling the orchestrator alone
leaves the node jobs to Slurm's own cleanup, which usually ends them and
sometimes does not. Seen here for real: an orchestrator failed and its OpenROAD
detailed route went on running for another **1h47m**, while the store said the
node was cancelled. A cancel now names the node jobs, and a run that is found
gone has its survivors reaped.

⚠️ Only the jobs the scheduler still has are scancelled. `scancel` answers an
error for one that has already finished, and a warning per finished node is how
an operator learns to ignore warnings.

### Two partitions, and which work goes where

```
compute*     a node's task -- EDA tools, real cores, real memory
coordinate   the run's own orchestrating process
```

The orchestrator loads the manifest, drives the flow, and submits every node as
a job of its own. It computes nothing and holds one core for as long as the flow
takes, so on a single-partition cluster it is the most expensive idle process
there. `entrypoint.sh` seeds `/sc_server/config.json` with
`"batch_queue": "coordinate"` to put it in its own; edit that file in the volume
and the edit survives restarts, because it is only ever seeded when absent.

Both partitions cover the same nodes, because this stack has one. A real cluster
would give `coordinate` a small machine of its own — `MaxCPUsPerNode=4` stands
in for that here, capping what it can take so compute work cannot quietly end up
living in it.

`compute` is `Default=YES`, which is what a node's task gets when nothing names
a partition, and what `get_slurm_partition()` finds via the `*` that `sinfo`
appends.

This stack can run it. The image carries `crun` (the OCI runtime Slurm invokes
— a binary it execs, so no socket and no daemon), plus `skopeo` and `umoci` to
turn a registry reference into a bundle, and `oci.conf` tells Slurm how to call
crun. A `registry` service on the internal network gives images a real
repository digest, which a locally built image does not have and which is the
whole point of pinning one.

`bootstrap` does all of it on `docker compose up`, and the pair of published
images is the point rather than a convenience:

| | |
|---|---|
| `sc-runtime` | SiliconCompiler and the Slurm client, no EDA tools — **0.6 GB** |
| `sc-tools` | the compute node's image: the same SiliconCompiler, plus the tools — **6.5 GB** |

A node that runs no tool resolves to the small one, because among the images
that fit, the one with the fewest declared contents wins. So does the run's
orchestrator. Only a node whose tool lives in the big image pulls the big image.

⚠️ **Which tools are declared is the sharpest edge here**, and it is the
`TOOLS` list in `bootstrap.py`. A tool that is in the image and not in the
registry raises no requirement, so its node resolves to the framework image and
fails inside a container that never had it.

🔴 **`sc-runtime` carries the Slurm client, and it is not optional.** A
framework image submits every node of the flow it drives. That is ~10 MB of
plugins beside `libslurm`, copied from the same build the cluster runs so the
two cannot drift, against ~6 GB of tools left behind.

### What a container has to be able to see

A bundle is a root filesystem, so anything outside the image has to be bind
mounted in. `container_mounts` in `/sc_server/config.json` is that list, and the
data directory is always added because every path in a job's manifest is under
it. This stack names three more:

| | |
|---|---|
| `/run/munge` | the socket `slurmctld` authenticates the container through |
| `/sc_tools/etc` | where `slurm.conf` lives |
| `/etc/resolv.conf` | 🔴 or the container cannot **resolve** `slurmctld` |

That last one is the least obvious and the most misleading. Slurm builds its own
runtime spec from the bundle's and does not carry over the `resolv.conf` bind an
unpacked image has, so the container gets the image's own — empty, on a bare
Ubuntu. It fails as `Unable to contact slurm controller (connect failure)`,
which reads like the controller being down.

⚠️ **Changing the list does not restage bundles that already exist**: the mounts
are written into each `config.json` when it is unpacked. `rm -rf
/sc_server/images` and re-stage.

Until then this is the deployment the switch defaults to: SiliconCompiler is
advertised from the version the server process was installed with, both
`image_id` columns stay `NULL` for the life of every job, and nothing is
degraded by it.

To exercise the registry on a host that *can* run containers, turn it on in the
server's datadir and register at least one image — a deployment that runs
containers and has none does not start, which is the check catching the
misconfiguration at the cheapest possible moment:

```sh
echo '{"containers": true}' > <datadir>/config.json

python3 -m siliconcompiler.remote.server.registry -datadir <datadir> \
    add-software siliconcompiler -kind python
python3 -m siliconcompiler.remote.server.registry -datadir <datadir> \
    add-version siliconcompiler 0.38.9 -preference 10
python3 -m siliconcompiler.remote.server.registry -datadir <datadir> \
    add-image ghcr.io/siliconcompiler/sc_runner:v0.38.9 \
    -contains siliconcompiler==0.38.9

python3 -m siliconcompiler.remote.server.registry -datadir <datadir> list
python3 -m siliconcompiler.remote.server.registry -datadir <datadir> \
    resolve -versions siliconcompiler==0.38.9 -tools openroad
```

`add-image` resolves the tag to a digest once, at registration, and the digest
is what gets dispatched — so rebuilding the tag afterwards does not silently
change what jobs run. `resolve` answers *what would this job be placed in*
without submitting one, which is how to check a registry before a user does.

`-kind` is `python` or `tool` and it decides whether **one** image has to hold
the name or each node's image does: everything `python` shares the run's
interpreter, and a tool is resolved per node. A tool also takes `-driver`, the
module carrying its Task driver, which is what lets a probe read its version
out of an image:

```sh
python3 -m siliconcompiler.remote.server.registry -datadir <datadir> \
    add-software openroad -kind tool -driver siliconcompiler.tools.openroad
```

`add-version` normalises what you type to PEP 440 and prints the spelling it
stored, because `-contains` has to name the same string. For a tool that
reports no version, register the date its image was published and say so:

```sh
python3 -m siliconcompiler.remote.server.registry -datadir <datadir> \
    add-version openroad 20260924 -unversioned
```

That lists the tool and lets a job that names no version run in it. What it
never does is satisfy a version range — `20260924` beats `2.0.1` under every
comparison there is, so a date that could match a range would outrank every
real release for ever.

To get a real version instead, ask the image:

```sh
python3 -m siliconcompiler.remote.server.probe \
    -python siliconcompiler -tool openroad=siliconcompiler.tools.openroad
```

It runs **inside** the image and prints one line of JSON behind a marker —
`importlib.metadata` for a python distribution, and for a tool its driver's own
executable, version switch and parser, which are the ones a real run uses. The
marker is there because a version check runs the tool, and a tool that prints a
banner writes to the same stream as the answer. The compose bootstrap does this
for every tool in its image and falls back to `-unversioned` only where nothing
answered.

Bundles are unpacked to `<datadir>/images/<digest>/`, which is the one thing in
this layout that is deliberately **not** per user: a root filesystem is
read-only and identical for everybody who runs that digest, so a copy per user
would buy nothing and cost one copy of every tool image per user. The run
unpacks a missing one before the flow starts, and the nodes waiting report
`preparing`.

## Adding compute nodes

```sh
docker compose up -d --scale scrunner=4     # or any N
```

The stack starts **two** by default. That is the smallest rig that shows a
single flow being spread across the cluster: every node is submitted to Slurm as
a job of its own, so with one runner the fan-out is real but invisible.

That is the whole of it — no config change, and the running services are not
restarted. The runners **register themselves**: each starts `slurmd -Z`
(Slurm's dynamic nodes), and the controller records the address and hostname it
registers with, so nothing has to know their names in advance. `slurm.conf` has
no `NodeName` lines at all; `Nodes=ALL` on each partition is what admits a node
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
- 🔴 **Restarting or recreating `scserver` alone leaves the cluster with NO
  NODES.** `scserver` runs `slurmctld`, and the runners are dynamic nodes:
  `slurmd -Z` registers at startup and appears in no configuration file, so a
  controller that restarts has no record of them. `sinfo` then reports `0 n/a`
  rather than anything that looks like an error, and every job queues for ever.

  ```sh
  docker compose restart scserver
  docker compose restart scrunner    # <- and this, in this order
  ```

  ⚠️ It bites exactly where it is least expected: editing `/sc_server/config.json`
  needs the server restarted, and the server shares a container with the
  controller.
- 🔴 **`server.db` has its own version and there is no migration.** A store
  written by a different shape of `schema.sql` is refused at startup, by name
  and with what to do about it. Move it aside and let the server create a new
  one; the old file stays readable with the server that wrote it.

  ⚠️ **Then `docker compose up` again** and `bootstrap` repopulates the
  registry before the server starts. That used to be a deadlock: a new store
  has an empty registry, a deployment with `containers: true` and nothing
  registered refuses to start, and the tool that would have fixed it needed the
  server running.
- 🔴 **The rig advertises the version this checkout's SiliconCompiler
  reports** — see the top of this file for why that is the last tag. The build
  log still says which commit is in the image.
- ⚠️ **`docker compose up` does not rebuild after a source change.** That is
  ordinary compose behaviour and it is the one thing the single command does
  not do for you: `--build` when you have edited something.

## What the shared mount looks like

The server is given `-datadir /sc_server` (a named volume) and lays it out
itself:

```
/sc_server/server.db                     the job store
/sc_server/config.json                   the policy overlay, if there is one
/sc_server/images/                       the OCI bundles Slurm runs
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

## What gets reclaimed, and when

🔴 **On startup, and nothing else reclaims anything.** Before this the rig
filled its disk quietly and fast: **28 GB on the data volume after one
afternoon of rebuilds, 25 of it container bundles nothing could run any more.**
Every `--build` produces a new image digest, which supersedes the old registry
row and leaves its six-and-a-half gigabyte unpacked bundle exactly where it
was.

| | |
|---|---|
| **bundles** | an image unpacked onto the filesystem, once no live image and no unfinished job names it. The largest by far |
| **artifacts** | bytes whose retention has passed. The row stays — *where did my results go* has to stay answerable |
| **builds** | a job's working tree, once nothing it produced is still reachable. It is what the artifacts were indexed **from**, so it may only go after them |
| **uploads** | an archive staged for a job that was created and never submitted, past its own grant's expiry |

⚠️ **Startup and nowhere else, deliberately.** A background thread is machinery
this profile does not need — a rig is restarted constantly, and a deployment
that runs for months wants a real scheduled job rather than something a web
process does when it feels like it. What it must never be is a surprise inside
somebody's request.

⚠️ **A job with no artifacts at all keeps its tree.** That is a run whose
indexing failed or has not happened, not one whose results expired, and its
tree is the only copy.

## Credentials

The MariaDB root password is random and discarded; `slurmdbd` connects as an
unprivileged user, and the database port is not published to the host. The one
credential is that user's password, overridable and defaulted for local use:

```sh
SC_SLURM_DB_PASSWORD=... docker compose up --build
```
