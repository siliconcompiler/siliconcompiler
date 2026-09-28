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

### 1. A node archive carries a pass-through output as the file, not the link

Surface D159 has a produced archive keep a link that resolves inside it. ⚠️
**A node archive leaves out the node's `inputs/`, and a task's pass-through
output is a link into `inputs/`** -- SiliconCompiler links it with
`link_symlink_copy` -- so kept as a link it arrives dangling: for a user
downloading the node, and for a run continuing from it (surface D175), whose
copy of the node's outputs would be missing exactly the files passed through.
This profile stores a link that resolves to a regular file inside the job as
that file's bytes in the node archive, as it already did for `input`. A link
to anything else inside is kept as a link; one out of the archive is dropped,
as D159 says.

**Where it goes:** surface D159's produced-archive rule, and D175's *what
arrives* -- the node's outputs as files.

### From follow-on 14 (the `v1` review, in code)

#### 2. Host mode records no install in `resolved_versions`

Surface *How it is built* has `resolved_versions` list what the install added,
with any version substituted within its release line. A derived image records
it, in `images.installed`. ⚠️ **Where nodes run on the host there is no image**:
the install still runs while staging, from `package_indexes`, and substitutes
within the release line, but nothing on the job keeps what it installed, so
`resolved_versions` lists neither the host's own versions nor the additions.
It is the logs that say. A column for it, or a statement that
`resolved_versions` is images only, closes it.

**Where it goes:** surface §17's `resolved_versions` bullet.

#### 3. The grace window is 300 seconds

Contract *A refresh token stays usable for a few minutes after it is replaced*
leaves the number to the server. `sc-server` uses 300 seconds
(`REFRESH_GRACE_SECONDS`): a repeat of the replaced token with a valid proof
from the family's key gets the pair already issued, and after that it is
reuse, ending the family with `reused`.

**Where it goes:** the profile, as the value this deployment uses.

#### 4. A refused create binds no key

Surface §6, *Idempotency*, binds a key on a final answer: a `2xx`, or a
refusal without `Retry-After`. ⚠️ **A refused create does not bind here.**
`sc-server` keeps a create's key on the job row, and a refused create writes
none, so a retry with the same key is evaluated again rather than replayed --
it can succeed where the first was refused. Submit keys do bind as the
contract says, on the job they were sent for.

**Where it goes:** surface §6's *Idempotency*: allow it for create, or have
`sc-server` keep refused creates' keys.

#### 5. A replayed submit returns the original `202` body

Now that submit answers early, a replay with the same key and body returns the
`202` body stored when the key was bound (`jobs.submit_reply`), not the job as
it stands. A client reads the job's progress from the poll, as it must after
the first answer.

**Where it goes:** surface §15, beside *Submit answers `202` in `staging`*.

#### 6. `api_fetchable_kinds` is kept, as a test knob

The profile has no kind that needs an approval and no controlled resources.
`api_fetchable_kinds` stays in `sc-server`'s config, off by default and used by
test modes 2 and 3, and a kind it leaves out gives the ladder's own answer for
a kind needing an approval: row 7, `fetchable: false`, `403
artifact-not-approved`, with no `access_request_url`.

**Where it goes:** the profile's §6 table, as a test mode.

#### 7. Item 20 is met by the startup check

*Every check that reads the manifest, and the manifest the run loads, use the
SiliconCompiler the job resolved to* holds here by the second route that
paragraph allows: `sc-server` refuses to start while it advertises a
SiliconCompiler newer than the one it runs, so re-derivation never reads a
manifest newer than itself. It does not re-derive inside the job's image.

**Where it goes:** the profile, naming which route it takes.

#### 8. `sc_configs/` in an upload is `unrequested_member`

The first archive's allowed members are the manifest at its root,
`sc_collected_files/`, `sc_python/` and each upstream node's `outputs/`. The
old client's `sc_configs/` scripts, and `sc-server-progress.json`, are
therefore `archive-rejected`, `reason: "unrequested_member"`; the server keeps
its own run state outside the extraction root.

**Where it goes:** surface *What the archive carries, and who decides*, as an
example.

#### 9. The stream URL's `ended=1` is unsigned, and a nonce `n` is signed

A stream URL serves one connection, so each URL `/logs` hands out carries a
nonce `n`, covered by the signature. A finished node's URL also carries
`ended=1`, which is not signed and grants nothing: it only has the stream send
its `end` at once. Both are this host's business, since the stream URL is
opaque to a client.

**Where it goes:** the profile's *stream host is this host* section, as
mechanism, if anywhere.

#### 10. Some interruptions are not yet `run-interrupted`, and a memory limit is not named

A job the scheduler loses ends `failed`, `run-interrupted`, with its running
nodes `failed` under the same type. ⚠️ **Node-level preemption, a Slurm
`NODE_FAIL` and an image that would not pull are not told apart from a node
that failed**: they end the node `failed`, `run-failed`. A time limit is named
in `detail`; a memory limit is not.

**Where it goes:** nothing in the contract changes; this is `sc-server` short of
it, and the profile should say so until it is not.

#### 11. Windows modes on the session store are best effort

`~/.sc/auth/` is `0700` with every file `0600` on POSIX, checked on every use.
On Windows the client grants the user alone through `icacls` when it creates
the store, and does not check an existing store's ACL.

**Where it goes:** identity *Where the CLI keeps it, and the mode is
normative*, as the Windows rule.

#### 12. No automatic re-registration on a local socket

Implementation-notes §O allows a subject's key to be re-bound automatically
where the operating system verifies the uid, on a unix socket or loopback.
`sc-server` does not: a changed key is `invalid_client` wherever it comes from,
and `registry release-binding` is the one way back.

**Where it goes:** nothing to change; the profile should say it is not built.

#### 13. `-from` is never widened, through a scheduler hook

Surface *The admitted window* forbids widening `option,from` in the server's
run. SiliconCompiler's scheduler widens it where an upstream result is
missing; the runner turns that off through `Scheduler.widen_from = False`, so a
node whose upstream results lack a file fails, naming it. The hook is
SiliconCompiler's, and nothing else sets it.

**Where it goes:** nothing to change; implementation-notes, as the mechanism.

#### 14. The profile counts 19 kept tables and lists 20

The profile's §3 is *19 tables of 41*, and implementation-notes §O lists 20:
`users`; four session and device tables; seven job tables, `job_continuations`
among them; three artifact tables; `user_limits`; and four software and image
tables. `sc-server` keeps those 20.

**Where it goes:** the profile's §3 heading and §O's *Kept, 19 tables of 41*.

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
