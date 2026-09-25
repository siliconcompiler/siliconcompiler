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
`reported` parse (2), the job log stream (3), what the archive carries (4), and
the eleven this file then held (5: surface D107–D111, entitlements D28, profile
D27) — were decided in `crucible/orchestration/api/contract-changes.md`, are
implemented here, and have been removed rather than edited. Their home is the
contract now.

---

## Open — not yet in the contract docs

### 1. The manifest does not record which copy a resource resolved to

D111 closed *where does a job record that it ran on an uploaded copy* with
**"the manifest already records where each file resolved from"**, and asked
that a node's manifest show it unambiguously. ⚠️ **It does not.** A
SiliconCompiler manifest records each dataroot's **registered source** — its
`path` and `tag` — and nothing about where a file was **resolved** at run time.
The collected copy wins silently: `resolve_path` checks the collection
directory before the original path, and no parameter anywhere says that it did.

So the requirement cannot be met by recording into an existing field. What it
needs is one of:

- **a schema addition** — a per-node `record` of where each dataroot resolved,
  or of which dataroots resolved to the upload — which is a SiliconCompiler
  schema change with its own version bump; or
- **the server rewriting an uploaded dataroot's `path`** in the manifest it runs,
  to the job's collection directory. Collected files are found by the dataroot's
  NAME, so resolution is unaffected, and the node manifests then say where the
  resource came from — at the cost of no longer recording the submitter's
  original source.

This profile logs the use of an uploaded copy and records nothing else, pending
that choice.

**Where it goes:** `surface.md` D111, and SiliconCompiler's schema if the first.

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
