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
D27), and 6–8: the server never reads a path a job names, the fetch allowlist
and its globs, create as a lookup and the fetch while `queued`, the follow-up
archive, the upload grant's size, the registry changes (`download-too-large`,
`unsatisfiable-request` retired, `upload-forbidden`'s members), and the smaller
rows (surface D115–D128, profile D30) — were decided in
`crucible/orchestration/api/contract-changes.md`, are implemented here, and have
been removed rather than edited. Their home is the contract now.

The one item this file held open — **the manifest did not record which copy a
resource resolved to** (D111) — closed with them, by its second option: the
server points every dataroot of the manifest it runs at the copy it resolves
to, the job's upload or its own supplied root. A node's manifest now says so.

---

## Open — not yet in the contract docs

### 1. The contract's own error pages still name `unsatisfiable-request`

`server-errors/entitlement-denied.html` (*What this is not*) and
`server-errors/index.html` (the documented types) both name the slug D116
retired. This tree's copies say `resource-unavailable` instead.

**Where it goes:** `api/server-errors/`.

### 2. A `node` archive over a DELETED member is not on the ladder

D120's row answers a node archive with its worst member's refusal — withheld,
missing resource, pending — and names no answer for a member that was
**deleted** on its own. Here it cannot happen, since the node is the unit of
deletion, and the ladder answers the member's `not-found`. That would tell a
client the archive is gone when it is not; `artifact-not-approved` is probably
the right row, since handing the archive over would undo the deletion.

**Where it goes:** `entitlements.md`, the ladder's row 4.

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
