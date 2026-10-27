# What sc-server implements of the v1 API

`python3 -m siliconcompiler.remote.server` serves what the SiliconCompiler
client calls, and nothing else. It is a test server and a small single-site
server, not a multi-tenant service.

## Served

- `GET /v1` publishes the limits, `logs.stream` as its one feature, the
  `client_credentials` and `refresh_token` grants, and identity assurance
  `self_asserted`. `GET /v1/healthz` answers `pass` or `fail`.
- `POST /v1/auth/token`: a DPoP proof on every grant. The first key a subject
  presents is bound to it. Access tokens last 15 minutes, refresh tokens 7 days
  (sliding), and a session 12 days.
- `POST /v1/auth/revoke`, `GET /v1/me`, `GET /v1/devices`,
  `DELETE /v1/devices/{id}`.
- `POST /v1/auth/browser` and a portal: a single-use sign-in, a jobs list, and
  a job page with cancel, delete and each node's log.
- Jobs: create (with `Idempotency-Key`), `upload-grant`, the signed `PUT`,
  `submit`, list, get, `cancel` and `DELETE`. Remote sources are fetched by the
  run itself.
- Artifacts: the manifest, logs (the job's and each node's) and one archive
  per node, listed and fetched through a `303` to a signed URL.
- `/logs` for one node: a `303` to its archived log, or a live event stream
  while it runs.
- The error type pages at their `type` URLs.

Every session holds every scope, and every user may submit. A user sees and
acts on only their own jobs.

## Refused or left out

- `POST /v1/auth/device` answers `501` (`feature-unsupported`); only
  `client_credentials` identities (`local:<subject>`) exist. Nothing verifies
  who a caller is.
- A job that `continues_from` an earlier job is refused
  (`prior-results-unavailable`): every node of a flow runs in one job.
- A job that needs a feature not published, including Python packages
  (`python.env`), is refused (`feature-unsupported`).
- `GET /v1/jobs/{id}/logs` without `step` and `index` is refused
  (`feature-unsupported`, `logs.stream.job`).
- No terms, plans, entitlements, approvals, per-account limits, retention
  sweep, container or image registry, or job reuse.
- Archives are limited in size, member count and expanded size, and a flow in
  node count, as `GET /v1` publishes. The concurrent-jobs limit is 4 per user.

## Deployment

State is one SQLite file and the job trees under `-datadir`. With
`-cluster local` a run is a child process of the server; with `-cluster slurm`
it is one `sbatch` job that starts the runner, which submits each node through
SiliconCompiler's Slurm scheduler. The compute nodes need SiliconCompiler, the
tools, and the data directory at the same path.
