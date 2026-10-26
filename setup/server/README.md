# Local sc-server on a real Slurm cluster

A throwaway cluster for running SiliconCompiler's bundled remote job server,
`python3 -m siliconcompiler.remote.server -cluster slurm`, end to end. What it
accepts and refuses of the `v1` API is in [PROFILE.md](PROFILE.md).

| Service | Runs |
|---|---|
| `slurmdb` | MariaDB, Slurm's accounting store |
| `slurmdbd` | `slurmdbd` |
| `scserver` | `slurmctld`, `slurmrestd` and the API on port 8080 |
| `scrunner` | `slurmd`; runs jobs directly on the host, with SiliconCompiler and the EDA tools installed |

Every service is one image built on `ghcr.io/siliconcompiler/sc_tools`, in a
different role (see `entrypoint.sh`). The `sc-server-data` volume is mounted at
`/sc_server` on `scserver` and every `scrunner`: it is the server's
`-datadir`, so the batch job each run is submitted as finds its job directory
and the shared package cache (`/sc_server/cache`) at the path the server wrote.

## Bring it up

```sh
docker compose up --build              # http://localhost:8080
docker compose up -d --scale scrunner=4   # more compute nodes
docker compose down -v                 # also drops the munge key and job files
```

From a git worktree, pass the version to build (`SC_VERSION=0.38.9 docker
compose up --build`). `SC_TOOLS_IMAGE` picks the base image; it must carry the
Slurm version `_tools.json` pins, with `slurmrestd`.

Compute nodes register themselves (`slurmd -Z`); `sinfo` on `scserver` lists
them. The API is published on `127.0.0.1` only, because the server does not
verify who a caller is.

## Point the client at it and run an example

```sh
sc-config remote configure http://localhost:8080
python3 -m siliconcompiler.demos.asic_demo -remote
```

`sc-config remote show` tests the connection. `sc-config remote portal` opens
the server's browser view of your jobs.

## Notes

- The munge key lives in a volume, not the image, so a rebuild of one service
  does not change it.
- `slurmd` runs as a child of PID 1 on purpose: cgroup v2 derives its root
  from `/proc/1/cgroup`.
- Only `scrunner` gets extra privilege (`SYS_ADMIN`, AppArmor unconfined), for
  `slurmd`'s cgroup setup.
- Recreating `scserver` alone can leave the nodes unregistered (`unk*` in
  `sinfo`); restart `scrunner`.
- The database password is `SC_SLURM_DB_PASSWORD` (default `sc_test_only`); the
  port is not published.
- Daily CI runs both the ASIC and FPGA demos through this rig
  (`remote_server` in `daily_ci.yml`).
