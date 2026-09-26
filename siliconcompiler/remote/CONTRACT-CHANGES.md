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
D130–D140, entitlements D41, database D100–D102, profile D31–D32) — and the
four after them — links on every read of a job's tree, `run_hash`, forwarded
packages and framework distributions from the image (surface D159–D162,
job-reuse D15) — were decided in the contract docs, and have been removed
rather than edited. Their home is the contract now; follow-on 11 brings the
code up to the last four.

---

## Open — not yet in the contract docs

All from building a node's Python environment into a derived image (surface
D131's container mode, follow-on 10 part 5 step 4).

### 1. `--system-site-packages` does not see a virtual environment's packages

Build rule 5 has the build run *"in a virtual environment created from the
base image's Python with its installed packages visible
(`--system-site-packages`)"*. ⚠️ **Where that Python is itself a virtual
environment -- SiliconCompiler's images, with everything in `/venv` -- the new
environment sees the base installation's packages and not its parent's.**
Measured: from `/venv/bin/python`, `--system-site-packages` found the system
`numpy` in `/usr/lib/python3/dist-packages` and not the one in `/venv`, and
could not import SiliconCompiler's own dependencies. So pip would count the
image's cocotb as absent and install a second one: the failure rule 5 exists to
prevent, reached by following it. This profile also writes a `.pth` into the
build environment that runs `site.addsitedir` on each of the interpreter's own
site directories (their `.pth` files processed), and removes it from the
result. With it, cocotb-bus and cocotbext-axi install without cocotb and a pin
needing another cocotb is `uninstallable`, against an image holding cocotb in a
venv.

**Where it goes:** `surface.md` build rule 5 and D161 -- *its installed
packages visible: the interpreter's own site directories, which
`--system-site-packages` alone does not give when that interpreter is a virtual
environment*. And implementation-notes §L's *What it runs*.

### 2. The cache key is the base, the file and the constraints -- not the Python tag

Rule 7 keys the layer *"by base digest, Python tag and the file's content
hash"*, and database's `images.derivation` says the same. Two corrections:

- ⚠️ **The constraints are missing.** What an install means depends on what it
  was constrained by, and that is the job's `requires.python` names -- two jobs
  with one file and one base but different names can build differently. The
  versions they are pinned to are the base's, so the names are enough.
- **The Python tag is redundant, and cannot be known in time.** It is a
  function of the base digest, and only running the image says what it is --
  which the API process never does. Keying on it would mean starting a
  container to compute a cache key.

This profile keys on `(base digest, the file the server wrote, the sorted
requires.python names)`.

**Where it goes:** `surface.md` rule 7, `database.md`'s `images.derivation`
comment, implementation-notes §L's *What it caches*.

### 3. What a derived image installed has no column

*"`resolved_versions` lists what was installed"*, and a derived image holds no
`image_contents` of its own -- nothing an operator declared, and it must never
be a resolution candidate. ⚠️ **So the list has nowhere to be read from.** This
profile adds `images.installed`, JSON `[[name, version], ...]` as the build
found them in the layer, NULL exactly when `derived_from` is
(`CHECK ((derived_from IS NULL) = (installed IS NULL))`). A derived image's
contents are its base's plus these. It is excluded from resolution, from
`GET /v1`'s `software` and from the operator's image list (the portal shows it
apart, as *Built environments*), and reached only by `(derived_from,
derivation)`.

**Where it goes:** `database.md`'s `images` table, and the `resolved_versions`
paragraph of `surface.md` §17.

### 4. A build that fails for the server's reasons is `not-ready`, not `uninstallable`

The table names one answer for a build: `uninstallable`, *"a pin that will not
install for the target"*, and its fix is *the environment*. ⚠️ **A build can
also fail with nothing wrong in the pins** -- the index or the registry does not
answer, the build job is lost, it runs past its time -- and telling the owner to
change their environment would be false. This profile answers those `503
not-ready`, the job rejected, and tells them apart: pip reporting that it could
not reach an index is the server's failure, unless the builder's proxy refused a
host -- a wheel hosted somewhere the allowlist does not name -- which is
`uninstallable` and names the host.

⚠️ **Which slug is itself a question.** The registry defines `not-ready` as
`409` + `Retry-After`, for an output on its way; this profile uses it at `503`
for the server's own failure to prepare a job -- a build, a fetch that errored,
a framework bundle it could not unpack -- and did so before the builder. Either
the row widens to cover it, or the registry gains a slug for *the server could
not*; **recommended: widen the row**, since the client's answer is the same
(try again later) and a new slug is a freeze-time cost.

**Where it goes:** `surface.md` D131's *When / What is wrong / Answer* table,
one row: *while `staging` -- the build could not run -- `503 not-ready`, the job
rejected* -- and §7's `not-ready` row.

### 5. Over HTTPS the builder reaches a host, not a path

Rule 3: the builder *"reaches only allowlisted indexes"*, matched by the
allowlist's rules, paths included. ⚠️ **A proxy that does not break TLS sees
`CONNECT host:port` and nothing more**, so while the build runs an https entry
admits its whole host. The path rules still bind every index URL a file names,
at submit. Enforcing them during the build needs a TLS-intercepting proxy, with
its CA installed in every base image -- which this profile does not do.

**Where it goes:** `surface.md` rule 3, as a stated limit; implementation-notes
§L's *What it reaches*.

### 6. A question: may an index be a private address?

This profile's builder never connects to a non-public address, whatever the
allowlist says -- the rule every fetch this server makes follows. ⚠️ **That rules
out the shape the contract recommends against dependency confusion**:
*"allowlist one index that proxies PyPI"* is, in practice, a mirror on the
operator's own network. Either the address rule is lifted for `index_allowlist`
entries that name a host exactly (an operator's choice of one machine, which no
job can widen), or the recommendation says the proxy must be public.
**Recommended: lift it for exact hosts**, keep it for wildcards. This profile
keeps the rule until it is decided.

**Where it goes:** `surface.md` D131's dependency-confusion bullet, and the
address rule's statement of scope.

### 7. Where the layer is, and who puts it on the path

Rule 6 puts the layer *"on the tool's `PYTHONPATH` only"* and says nothing of
where it is or what does it. This profile installs it at
`/opt/sc/python-env/site` in the derived image, and the node's task adds that
directory to the tool's `PYTHONPATH` when it exists. ⚠️ **The task doing that is
the SiliconCompiler in the image, not the client's**, so the path is an
agreement between the builder and that code -- and the exact `siliconcompiler`
pin in `requires.python` becomes load-bearing: an image whose SiliconCompiler
predates the path would run the node without its packages and say nothing.
Also stated: a `.pth` file an installed package ships does not run from
`PYTHONPATH`, so a package relying on one (old-style namespace packages) is not
supported in the layer.

**Where it goes:** `surface.md` rule 6.

### 8. The builder, in this profile

For `sc-server-profile.md`'s *`python.env` only where there is somewhere safe to
build*:

- **`env_builder`** turns it on, needs `containers`, and is what advertises
  `python.env` where nodes run in containers; false is the switch.
- **A batch job of its own, in its own queue** (`build_queue`), on a compute
  node: the API submits it while the job is `staging` and waits for its result
  (`env_build_timeout_seconds`, 1800 by default). A queue of its own keeps a
  burst of builds from taking the slots flows are waiting on.
- **pip runs inside the node's image** in a container with a read-only root, a
  private `/tmp`, none of the image's mounts and a network namespace holding
  only a loopback, whose one way out is a unix socket to a proxy the build job
  runs. On a cluster that is itself containers, the compute node needs
  `NET_ADMIN` to bring that loopback up.
- **Pushed to the base's own repository**, under `sc-env-<key>`, so the registry
  must accept pushes from the compute nodes; staged as a bundle that borrows the
  base's root filesystem, so no tool image is unpacked twice.
- ⚠️ **Index credentials are not supported.** An allowlisted index that needs
  authentication fails the build as `uninstallable`.

### 9. The portal's session cookie is a bearer secret rule 3 does not name

Follow-on 11 asked for a check that nothing but the storage URLs is a bearer
secret on the wire in plaintext. The handover token passes -- single-use (spent
before it is checked), 60 seconds, opened by the CLI on its own machine -- and
the log stream's capability URL is the `303` target. ⚠️ **The session cookie the
handover mints does not**: possession is the whole of it, it lives twelve
hours, and it travels on every portal request. On loopback, which is how the
compose stack publishes the portal, it never leaves the host; on a lab network
in plaintext it is exactly what rule 3 says this profile MUST NOT issue.
contract.md settles the handover token and says nothing about what it becomes.
Two readings, and the owner's to pick:

- **the portal is loopback-only where the deployment is plaintext** -- the
  server refuses a portal request from a non-loopback peer unless it arrived
  over HTTPS -- which keeps the cookie on the host, like the token;
- **or rule 3 names the cookie**, as a secret it accepts beside the storage
  URLs, with its lifetime.

This profile changes nothing until it is decided.

**Where it goes:** `contract.md` §5 rule 3, and the portal-session bullet of
`sc-server-profile.md`.

### 10. Where the code and the registry disagree, from follow-on 11's review

Found bringing the code and the error pages up to the review; each is a raise
site the registry's row does not list, and the code is unchanged until it is
decided:

- **submit with no upload** answers `409 job-state-conflict`, which is not one
  of the row's three cases. **Recommended: the row lists it** -- the job's
  state, holding no bytes, is what does not allow the call.
- **submit re-checks `upload-too-large`** over every archive of the job, where
  §15 says submit raises no `413`. It cannot fire unless the grant's own check
  was bypassed. **Recommended: keep it as a backstop and say so in §15.**
- **create raises `node-limit-exceeded`** from `descriptor.flow.nodes`, which
  the create table does not list. It is the same early refusal as the others
  there, re-derived at submit. **Recommended: the table lists it.**
- **D38's reach.** The probe has no presence override: presence is `command
  -v` on the driver's `PATH`, and `bootstrap` declares only what the probe saw.
  But `registry add-image -contains` and the portal's registration form still
  declare an image's contents unverified, which `images.py` has always said
  outright. If *no operator override* covers manual registration too, both
  must probe before they write -- the portal cannot, since the API host runs
  no containers. **The owner's call.**
- **surface D124's decision row** still says *while `queued`* and *`queued →
  awaiting_input`*, where the endpoint text says `staging`.

**Where it goes:** §7's rows for `job-state-conflict`; §13's and §15's
refusal tables; profile D38.

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
