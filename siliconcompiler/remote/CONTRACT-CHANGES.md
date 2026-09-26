# Changes to port back into the `v1` contract

`sc-server` is a reference implementation of crucible's `v1` API, so anything
this repo changes about the **published shape** is a change to the contract and
not to a deployment. This file is the running list, kept here rather than in a
commit message because the contract docs live in another tree and the port is a
separate piece of work.

**Where it goes:**
[`api/surface.md`](../../../plans/crucible/orchestration/api/surface.md) for
endpoints and payloads, [`api/database.md`](../../../plans/crucible/orchestration/api/database.md)
for tables and vocabularies, [`api/sc-server-profile.md`](../../../plans/crucible/orchestration/api/sc-server-profile.md)
for what this profile serves.

🔴 **The freeze is the first tagged SC release whose `sc-server` answers
`GET /v1`.** Until then these are free. After it, an additive *response* member
has to be paired with a `GET /v1` capability flag so a client can tell whether
it is there.

⚠️ **`additionalProperties: false` on requests does NOT make an additive
request member cost a version bump.** A server accepting a new optional member
is additive — old clients do not send it. What costs is a client *relying* on
one, which needs a capability flag exactly as a response member does.

---

## Every list so far has closed

The nine of the first review, the five of the software-buckets review, the
fifteen of the third and the follow-ons after it — the `.*` spelling and the
`reported` parse (2), the job log stream (3), what the archive carries (4), the
eleven this file then held (5: surface D107–D111, entitlements D28, profile
D27), 6–8 (surface D115–D128, profile D30), 9 (surface D129), and the five this
file then held — D129's set, the deleted member, `input`, and `copy` (surface
D130–D140, entitlements D41, database D100–D102, profile D31–D32) — were decided
in `crucible/orchestration/api/contract-changes.md`, are implemented here or
being implemented by follow-on 10, and have been removed rather than edited.
Their home is the contract now.

---

## Open — not yet in the contract docs

### 1. Links are confined on every read of a job's tree, not only `input`

D133 confines a node-bound `input` to the job's build directory. ⚠️ **The same
attack reaches every other read the server makes of that tree**, because the
job writes all of it: a node's code can replace its own log, its manifest or
the run's progress file with a link, and the indexer copying the log, the live
tail streaming it, the portal showing it and the reconciler reading progress
all followed it. This profile now reads a job's tree only through one module
that opens each component relative to the last and refuses a link (race-free
with `dir_fd`), refuses a FIFO, and stores a link in an archive as a link.

**Where it goes:** `surface.md` D133 — *every* read of a job's build
directory, with node-bound `input`'s follow-inside as the one relaxation.

### 2. §13's descriptor has no `run_hash`, and job reuse needs one

The restructured create body lists `flow`, `needs`, `requires` and `sources`
under `descriptor`, and requests are strict. ⚠️ **Job reuse's hash is in
none of them** — `job-reuse.md` D1: *"The hash is a member of the create
descriptor"* — so a client sending one is refused `400` by the letter of §13.
This profile accepts it as **`descriptor.run_hash`** and refuses it at the top
level. Nothing in the reference client sends one yet.

**Where it goes:** `surface.md` §13's descriptor and its members table.

### 3. Forwarded packages travel beside the environment file

D131 says the user's own packages -- editable, local, VCS -- are *"their
directories, uploaded under the ownership rules and put on the node's
`PYTHONPATH`"*, and names no path for them. **Owner, 2026-09-26: beside the
file.** This profile sends them at
`python-env/<step>/<index>/packages/<name>/`, in the first archive with the
file; the node's task puts that directory first on the tool's `PYTHONPATH`. The
server accepts the subtree only for a node that has a file, and never parses
it. ⚠️ So they are outside the manifest and the owner table: the file's
presence is what brings them, not a keypath.

**Where it goes:** `surface.md` D131's *Where the file is* table.

### 4. What the image holds is left out of the file, not only SiliconCompiler

D131 builds the file *"less SiliconCompiler's own dependencies"*. ⚠️ **A cocotb
node needs cocotb in SiliconCompiler's own process** -- it sets the GPI up from
it -- and that process never imports from the environment layer, so cocotb has
to be in the image. **Owner, 2026-09-26: the image.** The task reports it as
`framework`; the client pins it in `requires.python`, so the job resolves to an
image holding the client's version, and the file leaves out everything
`requires.python` pins. Otherwise the simulator and SiliconCompiler would each
load their own cocotb.

**Where it goes:** `surface.md` D131 -- *less what the job's `requires.python`
pins*.

---

## Not ported, deliberately

- **A second database backend.** Asked about — MySQL in the compose stack,
  SQLite locally — and declined. Every SQL call already goes through one
  chokepoint in `Store`, so placeholders, the `sqlite3` references and the
  `"index"` identifiers are one place each; the schema is the wall. It has 12
  partial indexes, four of them UNIQUE, and one —
  `devices_dpop_jkt_idx … WHERE revoked_at IS NULL`, one live device per key —
  cannot be expressed in MySQL without a generated column, so the two schemas
  would differ in shape and not just in dialect. ⚠️ **Postgres is the far
  cheaper target** if this is ever wanted: it takes the partial indexes,
  `ON CONFLICT` and the expression indexes as written.
