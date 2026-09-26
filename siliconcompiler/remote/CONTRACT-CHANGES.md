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
D27), 6–8 (surface D115–D128, profile D30), 9 (surface D129), the five this
file then held — D129's set, the deleted member, `input`, and `copy` (surface
D130–D140, entitlements D41, database D100–D102, profile D31–D32) — the four
after them (surface D159–D162, job-reuse D15), and the ten from building a
node's Python environment (surface D169–D174, database D117–D119, contract
D42, profile D39–D40) were decided in the contract docs, and have been removed
rather than edited. Their home is the contract now; follow-on 12 brings the
code up to the last ten.

---

## Open — not yet in the contract docs

### 1. The builder's repository and credential, on a registry with no authentication

Profile D39 puts derived images in a repository of their own, pushed with a
credential scoped to it and held by the build job alone, so a build can never
write to an image an operator registered. ⚠️ **That protection exists only
where the registry authenticates.** This profile's registry -- the compose
stack's, on the cluster's own network -- takes anonymous pushes, so anything on
that network can already write to any repository, and a second repository and
a credential would buy nothing. **Owner, 2026-09-27:** keep the same registry
and the base's repository here. What this profile does keep of D39: derived
images are pushed and referenced by digest, never by a tag, and no container's
process holds `NET_ADMIN` -- it is crun's, on the compute node, for the build
container's loopback.

**Where it goes:** `sc-server-profile.md` D39 -- *the repository and credential
apply to a registry that authenticates; this profile's does not*.

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
