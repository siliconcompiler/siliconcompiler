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

## Three lists have closed

The nine of the first, the five of the software-buckets review, and the fifteen
of the third — plus the two follow-on decisions after it, the second
follow-on (the `.*` prefix spelling, and a `reported` version that does not
parse lands on `published_date`, never coerced), the third (the job-level
log stream, `logs.stream.job`, D102–D103 / profile D25), and the fourth (what
the archive carries, by owner, and `resource-unavailable` — surface D104–D106,
database D93–D94, entitlements D27, contract D34, profile D26) — were decided in
`crucible/orchestration/api/contract-changes.md`, are implemented here, and
have been removed rather than edited. Their home is the contract now.

⚠️ **One of them had been missed until the fourth follow-on turned it up:**
`software-unavailable` (D91, with `requirement` and `available`) was in the
contract's registry and not in this profile's, which answered a version no
image holds with `unsatisfiable-request`. It is implemented now, and the
registry here is the contract's 34.

---

## Open — not yet in the contract docs

### 1. Presence is the executable, and a version switch is a separate question

A tool whose driver names an executable and no version switch — `kepler-formal`,
`icepack`, `vcd2fst` — was untestable, because presence had been tied to being
able to ask a version. So nothing declared them, no image held them, and a flow
reaching for one was refused **although the binary was in the image**. That is
the `bsc` failure inverted: refusing a tool the image has.

Presence is now `command -v <exe>` and the version is asked inside that guard
only where there is a switch, so those three land as *present and mute* —
`published_date`, which is what that value is for.

⚠️ **One case this does not cover: a python wrapper around a program.**
`graphviz`'s task has no executable at all and drives the python distribution
of that name, so its presence is `PackageNotFoundError` — which proves the
wrapper is installed and says nothing about `dot`, which the wrapper shells out
to. A runtime image with the wrapper and not the binary answered *present*.
This deployment installs the system package so the claim is true; the probe
still cannot tell the two apart.

**Proposed:** a tool read through `version_package` MAY name the program its
presence depends on, separately.

**Where it goes:** `sc-server-profile.md`, beside the probe's traps.

### 2. `entitlement-denied` on an artifact has no legal `resource_kind`

§22 says a fetch of an artifact whose `fetchable` is false is `403
entitlement-denied`, and the registry makes `resource_kind` and `resource`
REQUIRED on that slug. **`resource_kinds` is closed — `pdk`, `tool`, `library` —
and an artifact is none of them.** This profile sends `resource_kind:
"artifact"`, `resource: <kind>`, which is a value outside the set a client is
entitled to build one enum from — the exact trap D70 kept `logs` out of it for.

It has a second raiser now: the test modes withhold whole kinds from the API,
so the refusal is reachable on purpose rather than only through `withheld_at`.

**Proposed**, one of:
- the slug's two members are REQUIRED only where the refusal is about a
  catalogue resource, and an artifact refusal carries `artifact_kind` instead —
  the member `not-ready` already uses for the same vocabulary; or
- where an artifact is gated on a resource (entitlements.md: *what an artifact
  is gated on*), the members name **that** resource — the PDK the GDS derives
  from — and a refusal gated on nothing catalogued uses `artifact_kind`.

**Where it goes:** `surface.md` §22 and the registry row.

### 3. A job stream's id has to carry every node's position

Implementing D103's *`id` is job-wide and monotonic*: **a single counter
satisfies the words and cannot be resumed** by a stream host that remembers
nothing about its callers. A counter says how far the job got; it does not say
how far each NODE got, and arrival order across nodes is not reproducible on
reconnect, so a server handed `Last-Event-ID: 41` has no way to know where any
file should restart.

✅ **What this profile emits:** `<total>-<o1>.<o2>…` in hex — every node's
delivered byte offset, in the job's fixed node order, led by their sum. The sum
strictly increases with every `log` event, so it is monotonic; the vector is the
position, so resuming needs no server-side state; and an id whose length or sum
does not fit this job (a per-node id, another job's) starts from the beginning,
because a replay is a nuisance and a skip is a lost log. The id stays opaque on
the wire.

**Proposed:** a sentence in D103 that the id must identify every node's
position, not only the job's progress, where the stream host is stateless —
with this encoding as the example, not as the rule.

**Where it goes:** `surface.md`, the job-stream rules table.

### 4. Two things a job stream cannot tell a client on reconnect

Both follow from the contract as written; neither is stated, and a client
written from the text alone gets each one wrong once.

- **`end` at once applies to a RESUMED request too.** A client whose stream
  expired mid-job, reconnecting with `Last-Event-ID` after the job ended, is
  answered `end {"reason": "terminal"}` and nothing else — whatever it had not
  read yet is not replayed. That is the D103 rule working as intended, and the
  recovery is the same as for the late request: the node archives. **But the
  text says "a finished job", which reads as a fresh request.**
- **`node_state` carries no `id`, so a resumed stream repeats it.** The server
  cannot know which `node_state` events a client saw before it hung up, so a
  reconnect reports again every finished node whose log it has already
  delivered. A client must treat `node_state` as idempotent — collecting
  `artifact_id` into a map by node rather than a list.

**Proposed:** both as ⚠️ notes under the job-stream rules.

**Where it goes:** `surface.md` §20.

### 5. `manifest` may be bound to a node, and a client must not assume one per job

This profile now indexes each node's own manifest as a `manifest` artifact with
that node's `step`/`index`, beside the job's (`step`/`index` null). It is what
carries the node's record and metrics, and inside the node archive only, a
deployment withholding archives withheld the record with them.

The contract permits it — `step`/`index` are null *for job-level artifacts*,
and nothing makes `manifest` job-level only — **but every sentence about the
manifest reads as though there is one**, and a client written from them picks
"the manifest" out of a listing and gets a node's. This profile's own client
did.

**Proposed:** the kinds table says `manifest` is job-level or node-bound, and
that the job-level one is the run's final record.

**Where it goes:** `surface.md` §21, the kinds table.

### 6. A tool's LOCAL scripts, which the rule as written leaves behind

D104's table says a tool's scripts go up *only when the tool's package is
installed editable*. **A script a user points a task at from a local path is
not a package** — it is the user's own file, and the server has no copy of it.
Read literally, it is left behind and the job fails on the node that runs it.

✅ **This profile applies the resource rule to tools too:** a tool's file goes
up when its dataroot's source is local **or** editable.

**Proposed:** the tool row reads *only when local or editable*, as the PDK,
library and FPGA rows do.

**Where it goes:** `surface.md`, the D104 table.

### 7. An env-var dataroot is "local", and that uploads foundry data

The rule judges a file by its dataroot's registered source, and a path such as
`$FOUNDRY_ROOT/…` is a local path. **That is SiliconCompiler's documented way
to reference a proprietary PDK without committing it** — so by the rule, such a
PDK is uploaded in every job.

This profile allows it (profile D26, no NDA boundary), and its server counts an
env-var path it can resolve itself as held — so a deployment that sets the same
variable to its own copy still refuses nothing. ⚠️ **On crucible the same
upload would meet `upload-forbidden`** for a controlled PDK — correct, but a
client that ran happily against `sc-server` fails there with a PDK the user
never thought of as "uploaded".

**Proposed:** say whether an env-var dataroot counts as local; if it does, say
so beside the trap, because it is the case the user has no reason to expect.

**Where it goes:** `surface.md`, D104.

### 8. `software-unavailable`'s members have no stated shape

The registry names `requirement` and `available` and not their form. This
profile sends `requirement` as one string, name then specifier
(`openroad>=3.0`, or the bare name), and `available` as a **list** of version
strings the live images hold for that name — `[]` when the name is held
nowhere, which is itself the useful answer.

**Proposed:** those two shapes, or others — but stated, because a client
rendering the list has to know it is one.

**Where it goes:** `surface.md`, the registry row.

### 9. Waiting on the contract: where a job records an uploaded copy

D106 agrees that a job which ran on a user-supplied copy of a resource must
record it and show it; **the field is not decided** (the likely home is a
member beside `resolved_versions`). This profile **uses the upload — SC
resolves the archive's copy first — and logs it**, and has invented no field.

**Where it goes:** `surface.md` §17, once decided.

### 10. All 34 `type` pages, and the 29 titles they fix

`server-errors/` had five pages of 31, and its README says **the pages are
where each `title` is fixed** — the registry does not carry them. This profile
now has all 34, in `siliconcompiler/remote/server/errorpages/`, and serves them
at `/server-errors/<slug>` on its own host (outside `/v1`, so D83 needs nothing).
The five that existed are carried over; the 29 new ones follow their
structure and rules — the action first, the confusable neighbour last, the
renamed slugs naming what they replaced, the four below-the-handler ones saying
an untyped answer is expected.

⚠️ **What the contract has to take back:**

- **The 29 titles** are this profile's registry strings (`errors.py`), now
  fixed by the pages. `entitlement-denied`'s was the one that already disagreed
  — the registry here said *that resource* and the page *this resource* — and
  the registry was changed to match the page.
- **`index.html` was stale**: 31 types, three missing (`software-unavailable`,
  `resource-unavailable`, `upload-forbidden`), and superseded one-liners. The
  new one lists all 34 in registry order.
- **`entitlement-denied.html`** gains `fpga` among the kinds, links to its
  neighbours now that they have pages, and `resource-unavailable` as a
  neighbour. Its *Waiting will not help* reads *Retrying will not change this*.

**Proposed:** the folder's home moves to this tree — the README already says
lifting it into SC is mechanical — or the pages are copied back as they are.

**Where it goes:** `api/server-errors/`.

### 11. A deployment that serves the pages says where, with `Link` `rel="help"`

The `type` URI cannot point at a deployment — D20 freezes it byte-identical so
a client can compare it against a constant — and the public pages are not
reachable from everywhere a refusal is read. So this profile sends, beside
every `problem+json` body **and on a job read whose job carries an `error`**:

```http
Link: </server-errors/not-found>; rel="help"
```

RFC 8288, a reference relative to the server's own root and never built from
`Host`. `sc-remote` resolves it against the URL it called and prints it in
place of the `type` URI, and remembers where the pages are so a failed job's
reason links there too. Nothing branches on it; the `type` is untouched.

**Proposed:** *a deployment that serves the `type` pages itself MAY send
`Link: <…>; rel="help"` on a refusal and on a read of a job with an `error`; a
client MAY display it in place of the `type` URI and MUST still branch on
`type`.* Additive — a client that ignores the header loses nothing.

**Where it goes:** `surface.md`, beside *The body*.

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
