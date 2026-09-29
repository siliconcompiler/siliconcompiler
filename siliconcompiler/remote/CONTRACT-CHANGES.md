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
for what this profile serves. Changes to SiliconCompiler's own code that the
remote work turns up go in [CORE-FOLLOWUPS.md](CORE-FOLLOWUPS.md) instead.

🔴 **The freeze is declared by the contract's owner once `v1` has been
exercised**, by crucible's own work and by users. No release, merge or date
triggers it, and nothing on the wire marks it (contract *What "the freeze" is*,
D51). Before it, any part of `v1` may change. After it, a new enumeration value
or error type is a break (D50); a new optional response member is additive,
because a client ignores a member it does not know; and a new request member is
paired with a `features` string (contract *So "proper versioning" means rarely
needing a new version*).

⚠️ **`additionalProperties: false` on requests does NOT make an additive
request member cost a version bump.** A server accepting a new optional member
is additive — old clients do not send it. What costs is a client *relying* on
one, which needs a `features` string saying the server takes it, as
`python.env` does for `python_packages`.

---

## Every list so far has closed

The nine of the first review, the five of the software-buckets review, the
fifteen of the third and the follow-ons after it — the `.*` spelling and the
`reported` parse (2), the job log stream (3), what the archive carries (4), the
eleven this file then held (5: surface D107–D111, entitlements D28, profile
D27), 6–8 (surface D115–D128, profile D30), 9 (surface D129), the five this
file then held — D129's set, the deleted member, `input`, and `copy` (surface
D130–D140, entitlements D41, database D100–D102, profile D31–D32) — the four
after them (surface D159–D162, job-reuse D15), and the ten from building a
node's Python environment (surface D169–D174, database D117–D119, contract
D42, profile D39–D40) were decided in the contract docs, and have been removed
rather than edited. Their home is the contract now; follow-on 12 brings the
code up to the last ten.

The sixteen of follow-on 14's list — a node archive's pass-through outputs,
host mode's `resolved_versions`, the refresh grace window, a refused create's
key, a replayed submit's body, `api_fetchable_kinds`, the startup check,
`sc_configs/` in an upload, the stream URL's nonce, the interruptions read as
`run-failed`, Windows modes on the session store, re-registration on a local
socket, `-from` never widened, the kept-table count, a parameter going up
whole, and the `+private` marker (surface D266–D275, contract D65–D66,
entitlements D71–D72, identity D87, profile D56–D62, database D142–D145,
job-reuse D22, client-v1-migration D4–D8) — were decided too, and removed the
same way. Follow-on 15 brings the code up to them, but for what the first item
below says.

---

## Open — not yet in the contract docs

### From follow-on 15

#### 1. A parameter still goes up whole, until `collect()` selects values

The contract keeps the upload per value (surface *A parameter may go up in
part*; client-v1-migration D7): each value goes up where its own dataroot says
it does, and the rest of its parameter stays behind. ⚠️ **The code is behind
it.** SiliconCompiler's `collect()` takes a whole `(key, step, index)`, so the
client still sends a parameter whole and refuses one holding a private value
beside one that goes up (`owners.PrivateBeside`), and the server still admits a
follow-up's other values of each parameter it asked into. The selecting
argument is SiliconCompiler's to add (CORE-FOLLOWUPS item 8); both ends move to
the per-value rule, and `PrivateBeside` goes, once it is merged here.

**Where it goes:** nothing in the contract; this entry goes when the code
catches up.

#### 2. A private source not held is refused while staging, not at create

Surface's `resource-unavailable` is raised at create for a source in `sources`
the server does not hold. ⚠️ **`sc-server` defers a private one to staging.**
`descriptor.sources` names a dataroot by owner and dataroot and carries no kind
(database D147), this profile has no catalogue to find a name's kind in
(entitlements D75), and `resource-unavailable` carries `resource_kind`. So
create lists nothing for it, and the manifest's read, which knows the kind,
refuses the job while staging: `rejected`, `resource-unavailable`, with its
kind and name. The job costs its upload before it is refused.

**Where it goes:** surface's `resource-unavailable` row: *at create where the
server can name the kind, else while staging*.

#### 3. The profile's gap paragraph overstates the gap now

Profile §6's *One gap: some interruptions read as `run-failed`* (profile D59)
says a node ended by an image that could not be pulled ends `run-failed`, and
that a memory limit is not named. ⚠️ **Two of its sentences no longer hold:**

- a node whose image the runtime could not pull, Docker's or a Slurm bundle's,
  is `run-interrupted`, and so is its job, with `detail` naming the image and
  the pull error in the job-level `logs`;
- a Docker out-of-memory kill is named in `detail` as a memory limit, read from
  the daemon's `oom` event for the node's labelled container, never from exit
  status 137.

Still true: preemption and a Slurm `NODE_FAIL` end a node `run-failed`, and a
Slurm `OUT_OF_MEMORY` is not named.

**Where it goes:** profile §6's gap paragraph and D59, narrowed to Slurm.

#### 4. Four columns beyond `database.md`

`sc-server` keeps, beside the tables `database.md` gives:

- `job_nodes.metrics` and `job_nodes.records`: each node's metrics and records,
  read once, as plain JSON, from the run's final manifest when the job ends,
  never through SiliconCompiler (contract §1). They are what the portal's
  metrics screen reads;
- `jobs.python_packages`: the create body's `python_packages`, as the grammar
  accepted it. Database D147 says it is stored on the job and names no column;
- `jobs.python_answered`: each distribution the job was sent back for, whose
  wheel replaces its listed entry (item 5).

**Where it goes:** `database.md`'s `job_nodes` and `jobs`, as the reference's
own columns.

#### 5. The wheel answering a `python` entry replaces its listed entry

Surface *Uploaded wheels* refuses a wheel whose distribution `requirements` or
`constraints` also names: `archive-rejected`, `python_package`. ⚠️ **A
`python` entry names a listed distribution by construction**: the install
found no index with it. So `sc-server` remembers each name it sent the job back
for, takes that one wheel although the lists name it, and installs the wheel in
place of the entry. Every other overlap is refused as the surface says.

**Where it goes:** surface *Uploaded wheels*' no-overlap row: *except the wheel
the job was sent back for, which replaces its entry*.

#### 6. A wheel for a `requires.python` distribution is refused

The surface's overlap rule names the two lists and another wheel. A
`requires.python` distribution is never installed at all, since the image
holds it, so a wheel of one would be a second copy on the tool's path.
`sc-server` refuses it the same way: `archive-rejected`, `python_package`.

**Where it goes:** surface *Uploaded wheels*' no-overlap row.

#### 7. A compiled package asked for is cancelled, not rejected

Surface *How it is built* says a package asked for as a wheel that holds a
compiled file cannot be uploaded, "and the job is rejected, `uninstallable`,
naming it". ⚠️ **No endpoint lets a client reject its own job.** The client
stops, naming the package and its compiled file, and cancels the job; it ends
`cancelled`, with the reason in `state_reason`.

**Where it goes:** surface *How it is built*'s send-back bullet: the client
cancels, or the contract gives the client a way to decline an ask.

#### 8. How a package no index has is told from one that will not install

pip reports *no version of this project exists* and *no version of it installs
here* the same way. `sc-server` asks each configured index for the project's
page (PEP 503, `<index>/<name>/`): none has one, and the package is absent, so
the job is sent back for its wheel; one has, and the entry is relaxed to its
release line, then `uninstallable`. An index that cannot be asked is
`staging-failed`. An absent package is taken out and the install tried again,
so one trip asks for every one. In the builder the probe goes through the
build's proxy, and reaches only the indexes.

Host mode links what it installed at `sc_python/site` in the job's directory,
a link into the user's cache that the server writes after the upload is
extracted; an upload carrying `sc_python/` is `unrequested_member`.

**Where it goes:** implementation-notes §L's *On failure* row and *On the
host*, as mechanism.

#### 9. SiliconCompiler's side of the upload is short of the contract in three places

Each is SiliconCompiler's to change, and tracked in CORE-FOLLOWUPS:

- **An upload keeps links, and stores a linked file once** (contract.md).
  `collect()` follows links, so a link in a collected directory goes up as a
  copy of its target, and a file two values name under different dataroots
  goes up twice, once in each value's folder (CORE-FOLLOWUPS item 11).
- **The user's own modules go on the tool's path** (surface *A node's own
  Python packages*). Where a Slurm-dispatched run collects before it starts,
  `collect()` moves the uploaded collection aside and rebuilds it from the
  manifest's values, and a helper module, which is no value, is left behind
  (CORE-FOLLOWUPS item 9). Host mode and Docker are unaffected.
- **A dataroot the client resolved to local files resolves on the node to the
  uploaded copy, never by asking whether the package there is installed
  editable** (surface *Uploaded wheels*). The node's resolver still asks
  (CORE-FOLLOWUPS item 10).

**Where it goes:** nothing in the contract; each goes when its CORE-FOLLOWUPS
item is merged here.

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
