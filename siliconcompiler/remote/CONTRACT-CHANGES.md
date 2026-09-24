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

## Two lists have already closed

The nine items of the first, and the five of the software-buckets review
after it, were decided in `crucible/orchestration/api/contract-changes.md`,
are implemented here, and have been removed rather than edited — their home
is the contract now. What follows is everything found **while implementing
those decisions** that still changes the published shape.

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

⚠️ **And it is NOT bucketed, unlike `software` and the descriptor** — a
deliberate asymmetry worth confirming or overruling. Those two are split
because a reader has to know which names must land together when forming
requirements; this one is a record of what ran, and nothing is formed from it.
A flat map answers *what did this job run* directly. The cost is that a reader
comparing it to `software` meets two shapes for what look like the same thing.

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

### 7. `software.kind` is STATED at registration, not derived by probing

🔴 **This departs from the decision, which was *do not make this a field on
the registration form* — the two extraction mechanisms being the
classification.** It was implemented that way first and taken out, because the
derivation is not a derivation.

Deriving it means asking THIS process whether it can import the name or drive
it. That answers correctly for SiliconCompiler's own in-tree drivers on a
machine that has them, and quietly answers wrong for everything else — a site
library's tool, a proprietary driver, any name whose driver is not installed in
the API process. **A classifier that is right for the cases somebody checked
and silently wrong for the rest is the worst shape a derivation can have**, and
`kind` decides whether ONE image has to hold a name or each node's image does.

⚠️ **And there is nothing to derive FROM at the moment it matters.** The
process that registers an image is not the process inside it. Whether the API
host can import `openroad` says nothing about what the image holds.

So `kind` is an operator's statement: `-kind python` or `-kind tool`, and
naming a driver implies `tool`. The mechanisms are still the mechanisms — they
are just what the *probe* does with the answer rather than how the answer is
found.

**Where it goes:** `database.md`'s `software` table, replacing the derived-kind
note.

### 8. `software.driver`, which the contract has no column for

The probe has to import something to ask a tool its version, and **the module
cannot be worked out from the name.** `siliconcompiler.tools.<name>` is an
in-tree convention that nothing requires, and it is wrong in-tree already:
`kepler-formal` is driven from `siliconcompiler.tools.keplerformal`. Out of
tree it has no meaning at all.

So the module is recorded when the name is registered and handed to the probe:

```sql
driver text     -- 'siliconcompiler.tools.openroad'. NULL for a python
                -- distribution, and for a tool nobody here drives
CHECK (driver IS NULL OR kind = 'tool')
```

⚠️ **A tool with no driver is legitimate**, and is the case `published_date`
exists for: it is in the image, the deployment lists it, and nothing can ask
its version.

**Where it goes:** `database.md`'s `software` table.

### 9. The probe runs the command in the image and parses it outside

`version_source` distinguishes a reported version from a publish date, and
something has to do the reporting. The obvious shape is a module that runs
**inside** the image — and it was built that way first, and it is wrong.

🔴 **Most tool images are not SiliconCompiler images.**
`ghcr.io/siliconcompiler/sc_tools` is the one SiliconCompiler's own CI runs its
tools in, and CI installs the framework into it at test time. Requiring the
framework in every image an operator wants to register is requiring them to
rebuild somebody else's image.

So the split is: **the command runs in the image, the parsing happens where
SiliconCompiler is.** One shell script asks every name and frames each answer;
the caller runs it wherever it can start a container; the framing is read back
against the drivers.

```
python3 -m siliconcompiler.remote.server.probe -script \
    -python siliconcompiler -tool openroad=siliconcompiler.tools.openroad
```

Four things that only showed up against a real image, and every one of them is
a trap for the next implementation:

- 🔴 **A missing tool invents a version.** Unguarded, the shell's own
  `openroad: not found` lands in the frame, and OpenROAD's `parse_version`
  takes the last word — an absent tool registered at version `0`, parsed out
  of the message saying it was absent. Guard on the executable existing.
- 🔴 **A TTY changes what the tools print.** klayout colours its output when it
  thinks it is on a terminal, which put an escape in front of the marker
  closing its own frame: the frame never closed and a tool that HAD answered
  read as absent. Others wrap to 80 columns. Asking a program its version must
  not be a question about the terminal.
- 🔴 **The trailing newline is load-bearing.** A parser is entitled to count on
  what `subprocess` produces; bambu's takes `stdout.split('\n')[-3]`, so
  reconstructing the output without it reads the line above the version.
- ⚠️ **The frame is needed at all** because a version check RUNS the tool, and
  a tool that prints a banner writes to the same stream as the answer.

Not a wire change — but the *shape* is worth carrying, because every
implementation that wants honest `reported` versions meets all four.

**Where it goes:** `sc-server-profile.md`, as how this profile fills
`version_source`.

### 10. `requires` and `versions` are two members, not one renamed

The decision gives the descriptor `versions` (exact) and `requires`
(specifiers), bucketed. Implementing it: **a bucket with no `requires` falls
back to its `versions`, as exact pins.** That is what the single member meant
before, so a client that sends only what it has keeps the behaviour it had —
and *run it on exactly what I have* is a reasonable thing to mean.

🔴 **A flat map is REFUSED rather than guessed at.** Flattened, nothing says
which names have to land together, and guessing wrong resolves a node against
the wrong image while looking like it worked.

**Where it goes:** `surface.md` at `POST /v1/jobs`.

### 11. A requirement is a LIST of specifier sets, any one of which will do

The decision gives `requires.tools` one specifier per tool. That cannot say
what SiliconCompiler routinely means.

🔴 **A version requirement in SiliconCompiler is already a list.**
`Task.get('version')` holds alternative specifier sets and `check_exe_version`
accepts a tool that matches ANY of them. A requirement is declared **per task**,
so a flow with two tasks of the same tool has two lists — and one string per
tool has to either drop one or invent an intersection nobody asked for.

```jsonc
"requires": {"python": {"siliconcompiler": ">=0.38"},
             "tools":  {"openroad": [">=24Q3-2011", "==2.0"]}}
```

⚠️ **Alternatives are OR; a single set's commas are still AND.** A bare string
is the one-alternative case and stays legal. An **empty list is *any version of
this***, which is not the same as not naming the tool: it says the flow reaches
for it, which is what lets the server refuse before the upload.

**Per-node requirements were built first and taken out.** They are expressible
— tools already resolve per node — but they say the same thing once per node,
forty-two times for a flow, and the information that differs is the version
set rather than the node. The safety net is that a node's own
`check_exe_version` runs inside the container regardless, so image selection
being a little permissive ends in a clear per-task refusal rather than a wrong
run.

**Where it goes:** `surface.md` at `POST /v1/jobs`.

### 12. A specifier has to be normalised by the side that has the driver

🔴 **Normalising the stored version is only half of it, and the other half is
not optional.** OpenROAD declares `openroad>=24Q3-2011`. That is not a PEP 440
specifier at all, so a server given it raw cannot parse it, falls back to
comparing the string, and refuses an image that plainly satisfies it — *after*
the registry has carefully normalised what the image holds.

`Task.normalize_version` is the only thing that knows how to turn `24Q3-2011`
into `24.3.2011`, it is per tool, and it lives in the driver. So the CLIENT
normalises the requirement before sending it, keeping the operator and
normalising only the version, exactly as `check_exe_version` does before
comparing.

⚠️ **An unparsable part is dropped rather than forwarded.** It would match
nothing on the far side, which turns *this server has no version I can read*
into *this server has no OpenROAD*.

🔴 **And normalisation has to happen wherever a version is NAMED, not only
where one is written.** `verilator` reports `5.052`; PEP 440 stores `5.52`.
Registering an image whose contents named `verilator==5.052` — the number the
tool actually printed — was refused as *not a registered version*, by the
registry that had just registered it. Anywhere a version is looked up, it goes
through the same normalisation that stored it.

**Where it goes:** `surface.md`, beside the specifier rule — whoever implements
a client needs to be told this, because getting it wrong produces a refusal
that looks like a registry problem.

### 13. A tool no image holds is refused, wherever every node runs in a container

🔴 **This reverses a rule the profile states, and a live failure is why.** The
rule is that only a REGISTERED name raises a requirement — *a server that
curates images for the framework and says nothing about Verilator is not
claiming to have a Verilator image and is not refused for lacking one.*

That reasoning holds for a deployment running jobs on the host, which may
perfectly well have Verilator installed without anyone saying so. **It is
wrong once jobs run in containers, because then the registry IS the world.**

Observed: a Bluespec design was submitted to a deployment that had never heard
of `bsc`. Nothing raised a requirement, so its `convert` node was placed in the
**python-only** image, dispatched, and died on the first node with every other
node cancelled behind it. The cluster was paid for to learn something submit
already knew.

⚠️ **The discriminator is the driver, not a list of names.** A task declaring
an `exe` cannot run without that program; one declaring none runs in the
framework's own process and needs nothing from the image. A name-based rule
gets three cases wrong in two directions:

| | |
|---|---|
| `builtin` | joins, nops and minimums — no program, and already excluded by name |
| `execute` | runs a command the USER supplied, so there is nothing a registry could hold. A name-based rule would demand an image for it |
| `slang` | looks like a tool and is a Python binding. A name-based rule would refuse a flow that was always going to work |

⚠️ It costs building the task to ask, so it is asked ONLY where the answer
decides a refusal — never for a tool an image already holds. A deployment
holding everything its flows use never asks at all.

**Where it goes:** `sc-server-profile.md`, replacing the *unregistered tools
raise no requirement* rule with one conditioned on containers.

### 14. A tool's version can live in a python distribution under another name

`slang` is a tool to a flow — a node names it and has to be placed in an image
holding it — and it has no executable at all: its driver runs `pyslang` in the
framework's own process. So `kind = 'tool'`, and the version is read the
`python` way.

🔴 **And the distribution is not called what the tool is called.** The
registry's key is `slang`, because that is what the flow names and what the
resolution matches on; the version is `importlib.metadata.version("pyslang")`.
Nothing in `software` can record that mapping, so this profile keeps it in the
one place that knows its own images.

⚠️ **It also has to be declared by the SMALL image.** `slang` arrives with the
framework rather than with the EDA stack, so it is in both — and a tool
declared only by the big image drags every node that touches it into twelve
gigabytes for nothing. Each image declares what it actually answered for.

**Proposed:** `software` gains a nullable column for the distribution a tool's
version is read from — or the contract states that the mapping is a profile's
own business and says so, so nobody assumes the tool name is the package name.

**Where it goes:** `database.md`'s `software` table.

### 15. Two answers to *what version of SiliconCompiler is this*

Not a contract change, and it decides what a deployment advertises, so it
belongs on the list:

| | |
|---|---|
| `siliconcompiler.__version__` | from `_metadata.py`. What the client sends, what the bootstrap tags images with |
| `importlib.metadata.version(...)` | from the installed distribution. What the probe reads |

On a released install they agree. **On a development checkout they do not** —
`0.38.9` against `0.38.10.dev43+g20db24fa2.d20260924` — so the same deployment
answers differently depending on which one asked. They agree again inside an
image, because the wheel is built with the version pinned deliberately: the
Dockerfile derives the last TAG, since setuptools_scm would otherwise stamp the
dev version, and the image would then advertise a version no client asks for.

⚠️ **Worth stating because the honest answer is arguably the one nobody uses.**
An image built from 43 commits past `v0.38.9` contains `0.38.10.dev43` code and
says `0.38.9`. Nothing is inconsistent — the wheel really is stamped `0.38.9` —
but *what did this job run* is answered with a released version number for code
that is not that release.

**Where it goes:** nowhere in the contract. It is a note for whoever writes the
next profile, because the choice of source is theirs and both are defensible.

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
- **`software` has two buckets**, `python` and `tools`, a closed set with both
  always present. They are two because they are satisfied differently: the
  whole python set shares an interpreter and must be held by ONE image, and a
  tool is satisfied per node.
- **`images.built_at` breaks the tie two images with identical versions
  leave.** ⚠️ It is a TIMESTAMP and storing a date does not work — two images
  built on the same day is the ordinary case, not the rare one, so a date
  breaks nothing. And never `resolved_at`: that records when the operator
  pinned the tag, so registering a two-year-old image today would make it the
  newest.
- **No `python_only` flag.** Now that `kind` exists the derivation works — an
  image whose contents are all `kind = 'python'` is one — which is exactly why
  a boolean beside it would be a second source that drifts.

---

## Not on the wire, and deliberately

- **Browsing inside an archive** is a portal screen and not an endpoint. An
  API caller has the bytes; a person reading a report in a browser does not
  want to download a gigabyte to see one file.
- **`run_heartbeat_seconds`** is deployment config. No client sends a heartbeat
  or is told about one.
- **`version_source`** is a column and not a member. A bucket of `software`
  maps a name to a flat array of strings and that shape is frozen, so a version
  recorded from an image's publish date is advertised beside one a tool
  reported. Accepted in review: the preflight is advisory, the server is
  binding, and the refusal has to say *present but reports no version*.
- **`software.driver`** is not published either. It says where a Task driver
  lives so a probe can be handed it, which is an operator's concern and not a
  caller's.
