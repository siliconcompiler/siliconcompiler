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
one, which needs a capability flag exactly as a response member does. The
earlier wording here over-froze the request side.

---

## The first list is closed

The nine items this file carried through 2026-09 were reviewed and decided in
`crucible/orchestration/api/contract-changes.md`. They are implemented and
their home is now the contract, so they have been removed rather than edited:
`max_download_bytes` (renamed from `auto_fetch_max_bytes`, and a real limit
rather than advice), `run_heartbeat_seconds` taken off the wire, `reports` as a
produced kind, `error.detail` as a SHOULD, `error_type: "run-failed"`,
`deleted_at` keeping its writer with `deleted_reason` beside it, `user_limits`
without `plans`, no all-time `usage` figure, and `web_url`.

**What follows is the second list**, started the same way: everything found
while implementing those decisions that changes the published shape.

---

## Open — not yet in the contract docs

### 1. `deleted_reason` is the wire's spelling; the column is `delete_reason`

The review said *publish `deleted_reason` on the artifact object*, and that is
what is served. The column it comes from is `artifacts.delete_reason`, beside
`deleted_by`.

Both names are right where they are — in the table it reads as a property of
the delete, on the wire it reads as the explanation of `deleted_at` — but the
two pages will look like a typo of each other unless one of them says so.

**Where it goes:** `surface.md`'s artifact object, with a line in
`database.md` beside the column.

### 2. `resolved_versions` is a map of name to a LIST of versions

🔴 **Not name to version, and the single-value shape cannot be made to work.**
A forty-node flow over six tools resolves six images. Where the client pinned
nothing, two of those images can legitimately hold different versions of the
same distribution — the resolution picks per requirement set, and only the
pinned names are constrained across all of them. A single value would have to
choose one and be wrong about the rest.

A list per name is also what `GET /v1`'s `software` already is, so a client
that reads one knows the shape of the other.

⚠️ **Absent, never `{}`,** where nothing was resolved. A deployment that runs
jobs on the host has no image and no answer; an empty map would claim the job
ran nothing at all.

**Where it goes:** `surface.md`'s job object.

### 3. `job_identity` is computed at create, so it folds in the DECLARED resolution only

The review has `job_identity = H(client_hash ‖ the resolved image digests)` and
*resolve images at create as well as submit*, because that is what keeps the
create-time reuse check able to skip the upload.

🔴 **Those two together fix which digests are in it, and it is not all of
them.** At create there is no flow and no node list — the manifest is inside
the archive that has not been sent — so the only digests that exist are the
ones the DECLARED versions resolve to. Per-node tool images are resolved at
submit, after the upload the identity was supposed to avoid.

So the identity is over the declared resolution, and this follows from it:

⚠️ **Re-registering an image that only serves a tool requirement does not
invalidate reuse**, unless it also serves the declared set. Rebuilding an
OpenROAD image and re-running the same design returns the old job. The
alternative — folding in every live image that could serve the job — is
computable at create and deterministic, but it invalidates every reuse in the
deployment whenever any image is registered, which is a worse trade for a
feature whose whole point is not re-running work.

**Either the contract states the declared-only rule and its consequence, or it
needs a third option nobody has.** Recording the gap rather than hiding it.

**Where it goes:** `job-reuse.md`, and a line in `surface.md` at
`POST /v1/jobs`.

### 4. The download ceiling binds every route that yields artifact bytes

`max_download_bytes` is enforced on `GET /v1/jobs/{id}/artifacts/{id}`. It also
has to be enforced on `GET /v1/jobs/{id}/logs`, and that is not a second
policy: the log redirect hands out **the same signed URL** the artifact fetch
does, for an object of the same kind in the same table. A ceiling on one and
not the other is not a ceiling.

🔴 **Worth saying explicitly**, because the two endpoints are in different
sections and have different scopes (`artifacts:read` against `jobs:read`), so
the rule reads as belonging to one of them.

**Where it goes:** `surface.md`, at the limit's definition rather than at
either endpoint.

### 5. `detail` needs a stated bound, or every deployment truncates differently

`error.detail` is a SHOULD, with the condition that it must not echo
unvalidated input. This implementation bounds it: control characters removed,
whitespace collapsed to one line, 300 characters with an ellipsis.

That number is this deployment's guess. A client that renders a refusal in a
fixed-width box, or a log pipeline that indexes on it, sees a different
truncation from every server — which is exactly the sort of thing that reads as
a client bug.

**Proposed:** the contract states a maximum length and that `detail` is a
single line. Not what the maximum is — that is a deployment's choice — but that
there is one and it is stated in `GET /v1` or fixed in the contract.

**Where it goes:** `surface.md`'s error object.

### 6. `input` is in the profile's expected kinds and this deployment does not produce it

The produced-kinds list the review created has **expected**: `manifest`,
`logs`, `reports`, `input`, `node`; **optional**: `outputs`, `final`, `issue`.

`input` is the archive the client uploaded. This deployment deliberately does
not keep it: the client still has the bytes it just sent, and a second copy
costs the whole upload again for something nobody fetches. That is a
considered decision, not an omission.

So either `input` belongs in the optional set, or this profile is
non-conforming against a list written in the same review that accepted the
reasoning for not producing `reports`' large sibling.

**Where it goes:** `sc-server-profile.md`'s produced-kinds list.

---

## Already in the contract — implemented here, no change needed

Recorded so nobody re-proposes them.

- **`archived_at` has a writer.** D74 names the portal, and the portal writes
  it. ⚠️ The trap: `?archived=` has no value meaning BOTH, so its default is
  the one filter default in the profile that is not *everything*, and a screen
  that hides archived jobs needs an explicit way back to them.
- **Deleting an artifact is distinct from deleting the job.** `jobs.deleted_at`
  takes a job out of the collection; `artifacts.deleted_at` takes the bytes and
  leaves every row listed. ⚠️ And the unit is the NODE: a node's logs, reports
  and archive are three rows over one set of bytes, so deleting one of them
  frees nothing.
- **A job holding an unexpired upload grant is never abandoned**, however old
  it is. `abandon_after_seconds` is the floor and the grant's own expiry is the
  other half.
- **The contract allocates paths only under `/v1/`.** The portal, the storage
  routes and the log stream need no reservation — they are outside by
  construction. `/v1/portal` was proposed and refused.
- **`GET /v1`'s `limits` has nine members** in the contract. This profile
  publishes eleven: those nine plus `max_download_bytes` and
  `abandon_after_seconds`.

---

## Not on the wire, and deliberately

- **Browsing inside an archive** is a portal screen and not an endpoint. An
  API caller has the bytes; a person reading a report in a browser does not
  want to download a gigabyte to see one file.
- **`run_heartbeat_seconds`** is deployment config. No client sends a heartbeat
  or is told about one.
- **`version_source`** is a column and not a member. `GET /v1`'s `software` is
  a flat array of strings and its shape is frozen, so a version recorded from
  an image's publish date is advertised beside one a tool reported. Accepted in
  review: the preflight is advisory, the server is binding, and the refusal has
  to say *present but reports no version*.
