# Changes to port back into the `v1` contract

`sc-server` is a reference implementation of crucible's `v1` API, so anything
this repo changes about the **published shape** is a change to the contract and
not to a deployment. This file is the running list, kept here rather than in a
commit message because the contract docs live in another tree and the port is a
separate piece of work.

**Where it goes:**
[`api/surface.md`](../../../plans/crucible/orchestration/api/surface.md) for
endpoints and payloads, [`api/database.md`](../../../plans/crucible/orchestration/api/database.md)
for tables and vocabularies. What this profile serves is `sc-server`'s own, in
[`setup/server/PROFILE.md`](../../setup/server/PROFILE.md): a change there needs
no port. Changes to SiliconCompiler's own code that the remote work turns up go
in [CORE-FOLLOWUPS.md](CORE-FOLLOWUPS.md) instead.

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

The seven of follow-on 15's list — a private source refused at create by name,
the profile's gap narrowed to Slurm, the four columns, the wheel that answers a
`python` entry, a wheel for a `requested_versions.python` name, a client
cancelling what it cannot supply, and telling an absent package from one that
will not install
(surface D285–D287, profile D64, database D148, implementation-notes §L) — were
decided too, and removed the same way. Follow-on 16 brings the code up to them.

The two of follow-on 16's list — a cancelled job's reason on its transition, and
a cancel's reason at most 300 characters and served whole (surface D288) — were
decided too, and removed the same way. Follow-on 17 brings the code up to them.

The contract's own consistency pass (surface D289–D290, entitlements D76,
database D149–D150) came from no list here. Follow-on 18 brings the code up to
it, and moves the profile into this repository.

The Python packages review (surface D291–D296, entitlements D77, job-reuse D23)
came from no list here either. Follow-on 19 brings the code up to it, and found
nothing in it that `sc-server` could not serve as written.

What was item 1 here, *a parameter still goes up whole*, closed with `main`'s
#5459: `collect()` selects values, so the client sends each value on its own
and the server holds a follow-up to the values it asked for; `PrivateBeside` is
gone.

A dataroot named by its keypath (surface D298, implementation-notes §K,
client-v1-migration D13) came from no list here. Follow-on 20 brings the code
up to it. What it found was SiliconCompiler's, not the wire's: two dataroots of
one name collected a file of one path to one place. `main`'s #5465 fixed that by
bucketing each collected file under its dataroot's source, so a follow-up
archive's member under another task's dataroot of that name is told apart
wherever the two have different sources.

Follow-on 21's two -- a private entry with no source decided while staging, and
no credential in the uploaded manifest (surface D301, D302) -- were decided too,
and removed the same way. D301 is what follow-on 21 built. **D302 overturned
this file's earlier note that the owner left credentials in the manifest "for
now"**; the owner, 2026-09-30: *"the contract is right and I was lazy, lets
honor it correctly."* Follow-on 22 builds both halves: the client strips
userinfo and masks query values in every dataroot's path of every manifest it
packs, and `sc-server` refuses an archive whose manifest carries userinfo,
`archive-rejected`, `reason: "credential"`, naming the keypath.

The client review's two, operator headers for a stream host and a credential
from the environment (surface D304–D305, identity D90, client-v1-migration
D15), were decided too, and removed the same way. Follow-on 22 brings the code
up to them.

The client review's fourteen spec ambiguities (surface D306, identity D91,
contract D68, entitlements D81, client-v1-migration D16, ui/access D14) came
from no list here; follow-on 23 brings the code up to them, and to the one
handover route ui/access D15 and identity D92 put on both deployments.

---

## Open — not yet in the contract docs

### Waiting on SiliconCompiler's own code

Nothing to port: it goes when its plan lands on `main` and is merged here.

#### 2. SiliconCompiler's side of the upload is short of the contract in two places

- **The user's own modules go on the tool's path** (surface *A node's own
  Python packages*). Where a Slurm-dispatched run collects before it starts,
  `collect()` moves the uploaded collection aside and rebuilds it from the
  manifest's values, and a helper module, which is no value, is left behind
  (CORE-FOLLOWUPS item 9). Host mode and Docker are unaffected.
  **Tracked in:** [`collect/uploaded-collection-rebuilt.md`](../../../plans/siliconcompiler/collect/uploaded-collection-rebuilt.md).
- **A dataroot the client resolved to local files resolves on the node to the
  uploaded copy, never by asking whether the package there is installed
  editable** (surface *Uploaded wheels*). The node's resolver may still ask
  (CORE-FOLLOWUPS item 10).
  **Tracked in:** [`dataroots/decided-once.md`](../../../plans/siliconcompiler/dataroots/decided-once.md).

### From building follow-on 22 (2026-09-30)

#### 7. 🔴 An upload refused for a credential is kept, and keeps it

`archive-rejected`, `reason: "credential"` exists because the archive is kept as
the job's `input`, which anyone who can read the job can fetch (D302). But the
surface keeps an upload refused as `archive-rejected` as an `input` row
(*`input` is one per upload*), and excepts only `upload-forbidden`. So the
refusal keeps exactly what it refused. `sc-server` keeps it, as the text says,
and removes the extracted tree, which is a second copy of the same bytes.

**Proposed:** an upload refused for `credential` is not kept, as one refused
`upload-forbidden` is not: only the record of why remains.

**Where it goes:** `api/surface.md`, *`input` is one per upload*.

#### 8. A `-from` run's archive carries more manifests than the one D302 names

Each upstream node's `outputs/` carries that node's own manifest, and it
records every dataroot's path as the root manifest does. D302 has the client
send *each dataroot's path in the manifest it uploads* without its userinfo,
and the server refuse *an archive whose manifest carries userinfo*: the root
manifest. `sc-server`'s client masks every manifest it packs, the upstream ones
included, and its server checks the root manifest only.

**For the contract to say:** whether the rule and the refusal cover every
manifest an archive carries, or the root one alone.

**Where it goes:** `api/surface.md`, D302's bullet under *Every file is
uploaded or supplied by identity*.

#### 9. Two small things in D302's text

- **The `sources` example keeps userinfo.** §13 shows `"source":
  "git+ssh://git@github.com/acme/ip.git"` marked *credentials stripped*, but
  the rule removes all userinfo, `git@` included, as `safe_source` does, and
  the server refuses a manifest path carrying any. The example should read
  `git+ssh://github.com/acme/ip.git`.
- **"Naming the keypath" does not say where.** `sc-server` names each
  dataroot's keypath in `detail`. `resource-unavailable` carries a `keypath`
  member for the same purpose (D298), and `archive-rejected`'s registry row
  lists none; a client that wants to act on it has only prose.

**Where it goes:** `api/surface.md` §13 (the example) and the registry row for
`archive-rejected`.

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
