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
`GET /v1`.** Until then these are free. After it, an additive *request* member
costs a version bump (`additionalProperties: false` on requests), and an
additive *response* member has to be paired with a `GET /v1` capability flag so
a client can tell whether it is there.

---

## Open — not yet in the contract docs

### 1. `limits.auto_fetch_max_bytes` — a new published limit

| | |
|---|---|
| **Where** | `GET /v1` → `limits`, beside the other ten |
| **Type** | integer, bytes, per artifact. Default here: `104857600` |
| **Means** | the largest single artifact a client should pull without being asked for it |
| **Status** | **served**, and read by this repo's client |

🔴 **Why it is a limit and deliberately not `fetchable: false`.** `fetchable`
answers *may this caller have these bytes*, and the five client sentences
render a false one as deleted, withheld, aged out, blocked by an agreement, or
not entitled. Using it for size would tell somebody they lack permission to
read their own output. A published ceiling lets the deployment set the policy —
which is the point — without lying about what kind of answer it is.

⚠️ **It bounds one object, not the run.** Forty nodes each just under it still
fetch forty times it. A budget for the whole listing was refused because it
makes *what arrives* depend on *what order it arrives in*.

**Client behaviour to specify alongside it:** an object over the ceiling is
listed and not fetched; the client says so **once**, naming the total and the
ceiling, not once per object. An over-ceiling `bundle` must **not** displace the
other artifacts of its node — a bundle displaces what is inside it only because
fetching it gets you those bytes.

**A client that has never heard of it fetches everything**, which is why the
absence of the key has to stay meaningful.

### 2. `reports` is produced by this profile after all

| | |
|---|---|
| **Where** | [`sc-server-profile.md`](../../../plans/crucible/orchestration/api/sc-server-profile.md) — the produced-kinds list |
| **Was** | `manifest`, `logs`, `bundle`; `reports` and `outputs` explicitly not produced |
| **Now** | `manifest`, `logs`, `reports`, `bundle`. `outputs` is still not produced |

⚠️ **Not a vocabulary change** — `reports` is already one of the eight
`artifact_kinds`. What changes is the profile's claim that asking for it
truthfully returns `[]`.

**The argument that moved:** it is a second copy of bytes the bundle holds, and
that was the reason against it. It is now the reason *for* it, because of the
ceiling above: a node's reports are kilobytes and its bundle is often
gigabytes, so a bundle that is too large to fetch leaves the reports still
arriving. The doubling is small — the heavy things in a working directory are
the DEF and the database, not the reports.

### 3. `error.detail` on a job's error object

| | |
|---|---|
| **Where** | `GET /v1/jobs/{id}` → `error` |
| **Status** | already legal — the contract says *"an RFC 9457 object"* — but no example shows it and nothing said it SHOULD be there |

🔴 **Worth making explicit, because the object is useless without it.** `type`
and `title` are frozen and identical on every occurrence: *The run failed* is
true of every failed run there has ever been. A job's error with no `detail`
tells a caller nothing that `state` did not. Recommend: **SHOULD carry
`detail`** where the deployment has one, and say where it comes from — here it
is the exception that ended the run, recorded on the state transition.

### 4. `job_nodes.error_type` needs a writer

| | |
|---|---|
| **Where** | `GET /v1/jobs/{id}` → `nodes[].error_type` |
| **Status** | REQUIRED and nullable, and this server left it null on every node ever — including failed ones |

**Recommend:** a node in `failed` SHOULD carry `run-failed`. It is already one
of the three registry rows that are never an HTTP response and only ever a
`type` on an error object, so no new slug is needed — but nothing said which
one, and a published field with no writer is a published field that lies.

### 5. `usage` has no all-time figure, and should not grow one

Recorded as a **decision not to change the contract**, so it is not re-proposed.

`usage` answers *what am I consuming against my allowance*, and every window in
it is a calendar month for that reason. An all-time total has no allowance and
no reset, so putting it there means a published member with `limit: null`,
`window: null` and `resets_at: null` that a client must be told to ignore. The
portal computes and shows it; the API does not publish it.

### 6. `deleted_at` means *somebody decided* — say so

| | |
|---|---|
| **Where** | [`database.md`](../../../plans/crucible/orchestration/api/database.md) `artifacts.deleted_at`, and the artifact object in [`surface.md`](../../../plans/crucible/orchestration/api/surface.md) |
| **Status** | a clarification, not a change — but the absence of it produced a real defect here |

The column's comment says *"NULL `deleted_by` = the reaper"*, which reads as an
invitation for a retention reaper to set `deleted_at` when bytes age out. 🔴
**Doing that is wrong, and this repo nearly shipped it.** A client checks
`deleted_at` **before** expiry and renders it as *deleted on 24 Sep*, ahead of
every other reason — deliberately, because saying a thing expired when a person
removed it is the wrong answer that matters. So a reaper that sets it turns
every aged-out object into a report that somebody took it.

**Recommend:** state that `deleted_at` is set only where a **decision** removed
the bytes, and that retention lapsing is expressed by `expires_at` alone. A
reaper reclaiming expired bytes changes nothing on the row, because `fetchable`
is already false and no caller can have them either way.

### 7. Two more published limits: `run_heartbeat_seconds`, `abandon_after_seconds`

| | |
|---|---|
| **Where** | `GET /v1` → `limits` |
| **Status** | **served** |

Both exist because a job could get stuck in a state nothing would ever move it
out of, and in both cases the published number is the operator's patience.

- 🔴 **`run_heartbeat_seconds`** — how long a `running` job may go without its
  runner saying anything before the server stops believing it. Until this
  existed the ONLY way a dead run was detected was the scheduler forgetting
  it, so a node that vanished without deleting itself left Slurm reporting
  RUNNING for ever and the job with it. **The client half worth specifying:
  the runner writes the heartbeat on a TIMER, not on node transitions** — a
  single node can run for half an hour without one, so *nothing written
  lately* and *dead* are otherwise indistinguishable. ⚠️ **A progress file
  with no heartbeat means no opinion**, or an upgrade declares every in-flight
  job dead.
- 🔴 **`abandon_after_seconds`** — how long a job may sit in `created` or
  `awaiting_input` before it becomes `abandoned`. ⚠️ **It is a floor and not
  the whole rule:** a job still holding an unexpired upload grant is never
  abandoned however old it is, or setting this below the grant's own lifetime
  would kill uploads legitimately in flight.

### 8. `auto_fetch_max_bytes` appears in `GET /v1/me`'s `limits` as well

| | |
|---|---|
| **Where** | `GET /v1/me` → `limits`, which the contract defines as a six-member set |
| **Status** | **served**, as the seventh member |

🔴 **Because it is the only limit here that can differ per account, and
`GET /v1` cannot express that.** The capabilities block carries no credential,
so it cannot vary by caller — it publishes the deployment's default and
nothing more. A per-user ceiling therefore has nowhere else to go, and a
client must read the identity block for it.

✅ **The pattern is established rather than new**: four keys already appear in
both blocks, and the contract already says a client combines only those. This
makes it five.

### 9. `user_limits` joins this profile, without `plans`

| | |
|---|---|
| **Where** | [`sc-server-profile.md`](../../../plans/crucible/orchestration/api/sc-server-profile.md) — the 18-table list becomes 19 |
| **Status** | **built**, sparse and three-valued exactly as `database.md` specifies |

⚠️ **The contract pairs it with `plans` and this deployment takes only one of
the two.** A plan is a named tier and `user_limits` is the sparse override of
one; there are no tiers here, so what a NULL column inherits from is the
operator's `config.json` rather than a plan row. `plan_id` is therefore absent
and that is the whole of the difference.

✅ `-1` is unlimited in the column and `null` on the wire, per D16, and the
resolver is the only thing that knows.

⚠️ **The writer is the operator CLI, not the portal.** `database.md` files
`user_limits` under *an admin screen*, and this profile has no admin mode — so
the account screen renders it read-only and there is no endpoint.

### 10. `web_url` is served now, and the profile note that said otherwise was stale

| | |
|---|---|
| **Where** | the job object and the create response |
| **Status** | **served** — this is the contract being implemented, not changed |

Recorded because the reason it was absent is worth not repeating: the profile
omitted it with *"absent where the deployment serves no web UI"*, which was
true when written and became false the moment the portal landed. **A field
whose absence is conditional needs re-checking whenever the condition moves.**

🔴 The two rules that took care to honour: **absent, never `null`** — a null
would claim there is a portal and this job has no page — and **the origin
comes from deployment config, never `Host` or `X-Forwarded-Host`**, which is
tested with a poisoned forwarded header.

---

## Already in the contract, implemented here — no port needed

- `POST /v1/jobs/{id}/cancel`'s optional `reason` (D75). This client now always
  sends one — the caller's words, else *cancelled from sc-remote on `<host>`* —
  and the portal sends *cancelled from the portal*. **Worth a line in the
  contract as a SHOULD**: optional on the wire so a Ctrl-C stays expressible,
  and a cancel with nothing recorded leaves a job page that cannot answer the
  owner's own question.
- `preparing` as the eighth node state (D78).
- `state_changed_at`, `?design=`/`?jobname=` filters.
- 🆕 **`archived_at` has a writer at last** (D74). It was published on every
  job object and nothing had ever set it. The portal is the writer, which is
  what D74 intends — archiving is a view preference and not an operation on
  the run, which is why it has no endpoint. ⚠️ **The part that would have been
  a trap: `?archived=` is the one filter whose default is not *everything*,
  and there is deliberately no value meaning both** — so a screen that
  archives without offering a way to the archived list hides a job with
  nowhere to look for it.
- 🆕 **Per-artifact deletion, distinct from deleting the job.** `artifacts`
  already carried `deleted_at`, `deleted_by` and `delete_reason`, and only the
  job-level `DELETE` ever wrote them. 🔴 Worth a sentence in the contract
  because the distinction is easy to collapse and expensive to get wrong:
  `jobs.deleted_at` takes the job out of the collection, which is much more
  than a person means by *reclaim the space this run is using*.

## Not on the wire at all, and deliberately

The portal's archive browser — listing what a `bundle` or `reports` archive
holds and serving one file out of it — is **a screen and not an endpoint**. The
contract has no per-artifact path for exactly this reason: a client knows the
step, the index and the kind, and unpacks the archive where it came from. An
endpoint that indexed into an archive would put the server in the business of
understanding what a job produced.
