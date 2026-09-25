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
of the third — plus the two follow-on decisions after it, and the second
follow-on (the `.*` prefix spelling, and a `reported` version that does not
parse lands on `published_date`, never coerced) — were decided in
`crucible/orchestration/api/contract-changes.md`, are implemented here, and
have been removed rather than edited. Their home is the contract now.

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
