# The `sc-server` profile: what it serves of `v1`

What a client of `sc-server` sees: which parts of crucible's `v1` contract it
implements, which it refuses, what it publishes, and what it decides where the
contract leaves the choice to a deployment. How it is built, configured and
deployed is in [README.md](README.md).

This is a selection, not a second contract. Every endpoint, member, state and
error `type` here is the contract's, and every refusal is one the contract
already spells: there is no `sc-server`-only status, header or `type`, so a
client written against crucible reaches this server without a branch it did not
already have.

The contract is cited by document and section: `surface.md`, `contract.md`,
`identity.md`, `entitlements.md` and `database.md`, in crucible's
`orchestration/api/`. **A change to this file is `sc-server`'s own** and needs
no port back into them; a change to the published shape does
([CONTRACT-CHANGES.md](../../siliconcompiler/remote/CONTRACT-CHANGES.md)).

---

## 0. The one sentence

`sc-server` is the unauthenticated profile (identity §7) plus the image
registry (database §8), with one interface and no administrative mode.

Everything it leaves out falls to one of three tests:

| Test | Cuts |
|---|---|
| **Does it need a second identity?** | the device grant, the browser approval pages, CI credentials |
| **Does it need a grant, a plan or a signed agreement?** | `authorized`, terms, plans, projects, the artifact gate |
| **Does it need a human process?** | download approvals, access requests, elevation and view-as |

The floor is usability: a person can see their jobs, stop one, tidy up, and
revoke a machine's sessions.

`sc-server` is a reference implementation and a test server, scoped to a
single machine and SiliconCompiler's own CI. It is not built for a shared
multi-user cluster, and it makes no security claim: its multi-user mechanisms,
the key binding included, are best effort. Where nodes run on the host, a job
is not separated from other jobs or from the server.

Two limits are outside that scope, and not fixed:

- **A shared home directory.** Where login nodes share a home directory, one
  person is a different identity on each node, so a job submitted from one is
  not the caller's on another.
- **Revoking a device** ends that device's sessions. It does not keep out a
  machine that still holds the key: that machine can log in again.

---

## 1. Everyone is an admin of the portal; the API stays owner-scoped

Every user is an admin of the portal, so it has one interface and no second
mode ([README, *The portal*](README.md#the-portal)). None of that reaches the
API, where an administrator is an ordinary user:

- `GET /v1/jobs` lists the caller's own jobs.
- Every read and write of a job acts only on the caller's own; another user's
  job answers `404`.
- A job's id or hash is never a credential: holding one does not make a caller
  its owner.

---

## 2. The API: every endpoint, row by row

The numbering is surface.md's, and a removed endpoint leaves a gap: 6, 7 and 8
are unassigned.

| # | Endpoint | What `sc-server` serves |
|---|---|---|
| 1 | `GET /v1` | [below](#what-get-v1-publishes) |
| 2 | `GET /v1/healthz` | `status` alone: `pass`, `warn` or `fail`. Why it is degraded goes to the server's log, never to this unauthenticated answer |
| 3 | `POST /v1/auth/device` | routed, and refused in the OAuth shape with `400 unsupported_grant_type`, the contract's answer where `grant_types_supported` omits the device grant: the client's cue to use `client_credentials`. There is no approval page behind a `verification_uri` |
| 4 | `POST /v1/auth/token` | `client_credentials` and `refresh_token`, with DPoP on every session and no exception. The subject is bound to the first key that presents it ([§7](#7-the-key-binding)). A session lasts 12 days and is never extended; a refresh token 7 days, sliding; an access token 15 minutes. The refresh grace window is [300 seconds](#the-refresh-grace-window-is-300-seconds) |
| 5 | `POST /v1/auth/revoke` | ends the calling session, whatever its scope |
| 9 | `GET /v1/me` | [below](#get-v1me) |
| 10 | `GET /v1/devices` | the caller's devices. Never empty for a caller with a session: the key binding is the one real control this profile has, and this list is where a person sees it |
| 11 | `GET /v1/devices/{id}` | one of the caller's devices |
| 12 | `DELETE /v1/devices/{id}` | revokes it, ending every session it holds. See [§0](#0-the-one-sentence) for what it does not do |
| 13 | `POST /v1/jobs` | every descriptor check that has its input: `node_count` against `max_job_nodes`; `requested_versions` against `software`, the one SiliconCompiler included ([§5](#5-images-and-software)); `needs` against `features`; `sources` against what this server holds and fetches ([§3](#what-it-supplies-by-identity-and-what-it-fetches)). `project` is `501 feature-unsupported`, `feature: "projects"`. A `run_hash` is accepted; reuse is offered only where `jobs.reuse` is advertised ([§5](#5-images-and-software)) |
| 14 | `POST /v1/jobs/{id}/upload-grant` | a `PUT` to a signed route on this host, since `file://` storage cannot presign ([§2's divergence](#the-one-divergence-the-stream-host-is-this-host)) |
| 15 | `POST /v1/jobs/{id}/submit` | the contract's staging: the digest checked before anything is opened, then the archive, then the manifest, read by this server's own SiliconCompiler in a subprocess of its own ([§5](#5-images-and-software)), and the job's Python packages installed ([§3](#pythonenv-only-where-there-is-somewhere-safe-to-build)) |
| 16 | `GET /v1/jobs` | the caller's jobs, newest first, over a keyset cursor; `?project=` is `501 feature-unsupported` |
| 17 | `GET /v1/jobs/{id}` | the whole job object. `web_url` is served, since this profile has a portal. `resolved_versions` is absent where nodes run on the host ([§5](#5-images-and-software)). A failed node's `error` names what [§6](#one-gap-some-slurm-interruptions-read-as-run-failed) says it can |
| 18 | `POST /v1/jobs/{id}/cancel` | a `reason` of at most 300 characters, served whole on the transitions and on each node it stopped |
| 19 | `DELETE /v1/jobs/{id}` | deletes the job's data; the job object stays readable |
| 20 | `GET /v1/jobs/{id}/logs` | `logs.stream` and `logs.stream.job` are advertised, so a running node or job gets a `303` to a stream on this host; a finished one a `303` to its archived log |
| 21 | `GET /v1/jobs/{id}/artifacts` | [the kinds this profile produces](#what-it-produces) |
| 22 | `GET /v1/jobs/{id}/artifacts/{artifact_id}` | a `303` to a signed route on this host. `max_download_bytes` refuses, as `download-too-large`; a test mode may withhold kinds ([README](README.md#test-modes-serving-less-on-purpose)) |

### What `GET /v1` publishes

```jsonc
{
  "api_version": "v1",
  "software": {"python": {"siliconcompiler": ["0.39.1"]},  // one version: the one this
               "tools":  {"openroad": ["2.0.1"]},           //   server runs. Only what runs here
               "interpreter": {"python": ["3.12.4"]}},      // each image's own Python (§5)
  "grant_types_supported": ["client_credentials", "refresh_token"],
  "limits": { /* every member */ },     // the deployment's defaults
  "features": ["logs.stream",           // never "projects"
               "logs.stream.job"],      // + "python.env" only where configured (§3),
                                        //   "jobs.reuse" only where configured (§5)
  "identity_assurance": "self_asserted",
  "terms_url": …,                       // absent unless the operator sets one
  "notices": []
}
```

- A client branches on `grant_types_supported`, never on `identity_assurance`.
  Login ends at `POST /v1/auth/token`, with a token and no human involved.
- `identity_assurance` is `self_asserted`: this server does not verify who a
  caller is, and a client does not rely on the identity.
- `GET /v1`'s `limits` are the deployment's defaults, and `GET /v1/me`'s the
  caller's effective values. A key in both differs only where the operator set
  a per-account override.
- `max_staging_seconds`, in both, bounds one pass of staging: fetching, the
  manifest's read and the Python install. Past it the job fails
  `staging-timed-out`, `limit: "max_staging_seconds"`, and a job sent back and
  submitted again gets a fresh one. This profile has no plans, so it is the
  deployment's, from `config.json`'s `limits`, and the same for every account
  ([README, *The server's own settings*](README.md#the-servers-own-settings-in-one-place)).

### `GET /v1/me`

| Member | Here |
|---|---|
| `id`, `issuer` | `issuer: "local"`. `id` is what a client persists per server address, to tell *my jobs were deleted* from *I am a different person now* |
| `authorized` | omitted whole, never `{}`: this server does not do grants, capabilities included, so a client checks none ([§3](#pythonenv-only-where-there-is-somewhere-safe-to-build)) |
| `limits` | every member: the caller's effective values, the deployment's defaults unless the operator overrode one ([README, *The operator CLI*](README.md#the-operator-cli)) |
| `usage` | `concurrent_jobs`, `storage_bytes` and `compute_seconds` (run time in the calendar month), computed from the caller's jobs and artifacts; `license_seconds` is `{}`. Every `limit` is `null` |
| `can_submit` | always `true`, with no `blocked_type`: no service-scoped terms document exists to block it |
| `projects`, `terms` | `[]` |

### The one divergence: the stream host is this host

The contract serves `logs.stream` from a stream host on an origin of its own.
`sc-server` has one origin, so the stream is served from this host: a
capability URL with its own short lifetime, reached through a `303` like every
other. A `file://` store answers the artifact `303` and the upload grant the
same way, with a signed route here.

- Nothing on the wire changes. A client following the `303` attaches no token
  and no proof; after it, `text/event-stream` is the stream and any error
  status is a refusal.
- Authorization is still evaluated at `/logs`, and the stream a capability URL
  opens ends no later than the access token that obtained it.
- **Over plain http, the stream URL and the signed storage route are bearer
  secrets on the wire**: holding one is enough to read what it names until it
  expires. The contract's transport rule (contract §5, rule 3) permits both
  ([README, *Plain http*](README.md#plain-http-and-what-is-on-the-wire)).

---

## 3. What it keeps, produces and supplies

It keeps 20 of the reference schema's 42 tables
([README, *The tables it keeps*](README.md#the-tables-it-keeps)). A client sees
the ones it drops only as `authorized` absent, `terms` and `projects` `[]`, and
no gate on the bytes.

An operator may override a limit for one account, with the operator CLI; there
is no endpoint for it, and `GET /v1/me` shows the result.

### What it produces

The list lets a client asking for a kind tell `[]` meaning *none yet* from `[]`
meaning *never*.

| | Kinds |
|---|---|
| **Expected** | `manifest`, `logs` per node and one at job level, `staging`, `reports`, `node`, and `input` at job level, one per upload |
| **Optional** | `outputs`, `final`, `issue`, `input` bound to a node, and `diagnostics`, which this profile produces |

- **The server's record is never inside `logs`** (surface D295). The job-level
  `logs` is `job.log` alone, the run's own log.
- `staging` is what the server did before the run: a section per pass of
  staging -- the fetches, the manifest's read, what the Python install added or
  substituted, why the job was sent back -- scrubbed of this server's paths,
  host names and credentials.
  Where nodes run on the host, it is the record of what the install added
  ([§5](#5-images-and-software)).
- `diagnostics` is the operators' record: pip's whole output, the runner's own
  log, and what Slurm says of each batch job, job-level and per node. It is
  listed with `fetchable: false`, a fetch of it is `artifact-not-approved`, and
  the portal opens it.
- Job-level `input` is one artifact per upload, so what a job was sent can be
  read beside what it produced.
- Node-bound `input` is produced here and not on crucible, because this profile
  has no gate for a node's inputs to get round.
- `reports` is a second copy of bytes the node archive holds. It is expected
  because an archive over `max_download_bytes` is refused while a node's reports
  are kilobytes and still arrive.

### A tool no image holds is refused, where every node runs in a container

Where every node runs in a container, the registry is a node's whole
environment, so a tool no registered image holds is `software-unavailable`
rather than a node dispatched to fail with every node behind it cancelled.
Where nodes run on the host, a tool nobody declared may still be installed, and
is not refused.

### Uploading a PDK, library or FPGA device is allowed

The client uploads these when they are local or editable, and this profile
accepts them. There are no grants to hold a per-user permission, no NDA
boundary and no catalogue to match content against, so `upload-forbidden` is
never raised here. `resource-unavailable` still is: a flow naming a PDK this
server does not hold, whose files are not in the archive, is refused rather
than dispatched to fail.

### `python.env` only where there is somewhere safe to build

`python.env` is advertised only where the operator has configured the
environment builder, or where nodes run on the host. A containerised
`sc-server` with neither cannot build a node's Python environment, and refuses
to start if `features` lists it.

- **Who may use it: `python.env` alone decides.** This profile grants nothing,
  so none of the capabilities (`python-env`, `python-wheels`, `python-sdist`) is
  checked, and `entitlement-denied` with `resource_kind: "capability"` is never
  raised here. Building from source, crucible's `python-sdist`, is the
  operator's `python_source_builds`, off by default and only in the builder.
- **Where packages come from.** From PyPI, unless the operator configures other
  indexes. A job names no index, and the reuse of a built environment is keyed
  on the indexes too.
- **The exact version, or the client's wheel.** A version no index lists is
  sent back for, however many other versions of the name it lists. The newest
  of the release line is installed only where the version is listed and nothing
  of it installs here, or it is yanked, and the substitution is recorded. A
  package with only a source distribution is sent back for where it is pure,
  and `uninstallable` where another platform has a wheel.
- **Host mode's install.** Where nodes run on the host, a job's
  `python_packages` and its uploaded wheels are installed while the job is
  `staging`, into an environment of their own, named by what they install and
  with a pip cache of its own, under the same rules as a build: a package that
  will not install is `software-unavailable`, `reason: "uninstallable"`, before
  any node runs. What the install added is recorded in `staging`, fresh or
  cached alike, since there is no image to record it on.
- **What is inside a wheel is not looked at.** An uploaded wheel is held to the
  wheel rules and the archive's extraction limits; detecting content inside it
  -- a PDK's files packaged as Python -- is crucible's, against a catalogue
  this profile does not have.
- **An index that needs a credential** is not supported: the build fails
  `staging-failed`, naming the index, since the fix is the operator's.

How the builder is placed and isolated is in
[README, *The environment builder*](README.md#the-environment-builder).

### What it supplies by identity, and what it fetches

The server never reads a path the job names: a file the client left out is
never looked for at the same path on this host, with variables expanded from
the server's environment.

| Source | Here |
|---|---|
| **marked private** | supplied only from roots the operator configures, never outside them, or `resource-unavailable`. Never uploaded |
| **remote** | fetched only from the allowlist, whose default is the SiliconCompiler GitHub organisation: `github.com/siliconcompiler/` and `codeload.github.com/siliconcompiler/`, which is what lambdapdk needs |
| **not on the allowlist, and not held** | asked for at create, in `upload_sources`. A private repository behind the user's own key is the common case |
| **allowlisted, and the fetch fails for good** | fetched after submit, while `staging`; on failure the job goes back to `awaiting_input`, asking for that source alone |

A source whose query values the client masked (`?token=***`) says what it is
and not enough to fetch it from, so it is asked for rather than fetched.

---

## 4. The portal

`sc-server` serves a portal, which is why it serves `web_url`. A client sees
only the API; the portal's screens are in [README](README.md#the-portals-screens).

---

## 5. Images and software

The operator registers images, once, by digest; a submitter names versions,
which match a registered image or do not. A submitter who named an image would
choose what runs, and one who names a version chooses only from what the
operator registered.

- **A version is advertised only where it runs here**, so a client asking for
  an advertised version is never refused `software-unavailable`.
- **One SiliconCompiler: the one `sc-server` itself runs.** `software` carries
  `siliconcompiler`, in `python`, at that one version, and a job whose
  `requested_versions.python.siliconcompiler` it does not satisfy is refused at
  create, `software-unavailable` naming `siliconcompiler`. Where nodes run in
  containers, an image holding another is neither advertised nor used, and the
  server refuses to start if no live image holds its own.
- **The staging subprocess, and what isolates it.** While the job is `staging`,
  every read of its manifest runs as a subprocess of `sc-server`'s own
  SiliconCompiler, never in the server's process: the same staging step and the
  same checks as on every deployment, and the run loads the manifest with the
  same SiliconCompiler. A manifest whose SiliconCompiler version does not
  satisfy the job's declared one is `declared-mismatch`. The subprocess starts
  with an empty environment, so it holds no credential, and, as far as the host
  allows, has no network and sees only the job's own tree: in the job's own
  image where containers are configured, and in new user and network
  namespaces with resource limits of its own where nodes run on the host. There
  it is not isolated from the machine's files, which is within this profile's
  lack of a security claim
  ([README, *Where a job's manifest is read*](README.md#where-a-jobs-manifest-is-read)).
- **The interpreter is a bucket of its own** (surface D293). The probe records
  each image's `python3` as `software.interpreter.python`, and a job with a node
  running the user's Python sends `requested_versions.interpreter`, the
  client's `==<major>.<minor>.*`. Only an image running a matching Python places
  such a node; where none does, create is `software-unavailable` naming the
  versions there are, and a job that sends none is not held to one. Where nodes
  run on the host, the interpreter is this server's own.
- **`resolved_versions` covers images only.** Where nodes run on the host there
  is no image, so a job's `resolved_versions` is absent, and what its Python
  install added is in `staging`. Its `interpreter` is the Python of the images
  the user's Python ran in.
- **`jobs.reuse` waits for the host's tools.** A reuse hit compares the inputs
  the server supplied, the tools among them (surface §13), and a job run on the
  host records none. So `jobs.reuse` is not advertised by default, and the
  server refuses to start with it listed where nodes run on the host. Where it
  is advertised, a hit also needs the candidate's `python_packages`,
  `requested_versions.interpreter` and index configuration to equal the new
  job's (job-reuse D23).

---

## 6. Every refusal it makes is already spelled

None of these is new vocabulary.

| A client does | This server answers |
|---|---|
| `POST /v1/auth/device` | `400 unsupported_grant_type`, OAuth-shaped |
| sends `POST /v1/auth/token` or `POST /v1/auth/device` a request refused before any OAuth processing | `problem+json`, as on every deployment: `405 method-not-allowed`, `415 unsupported-media-type` or `429 rate-limited`. Only the OAuth answers are OAuth-shaped |
| names a `project` anywhere | `501 feature-unsupported`, `feature: "projects"` |
| `…/logs` | never `feature-unsupported`, outside a test mode that withholds streams |
| presents a known subject with a different key | `invalid_client` at the token endpoint, OAuth-shaped, wherever the request comes from, saying the subject is bound to a different key ([§7](#7-the-key-binding)) |
| reads `GET /v1/me` | `authorized` absent; `terms: []`; `projects: []`; `can_submit: true` |
| asks for a job or an artifact it does not own | `404`, not `403` |
| looks for `access_request_url` | never present: nothing here needs an approval, and a deployment without grants has nothing to request |
| fetches a kind a test mode withholds | `403 artifact-not-approved`, and `fetchable: false` in the listing, with no `access_request_url`, since this server offers no way to ask. Off by default |
| uploads a member with any extension | accepted: there is no extension allowlist, so `archive-rejected` never carries `reason: "extension"` here |
| exceeds a published ceiling | `limit-exceeded` naming the key as `limits` spells it, or a static one's own `type`: `node-limit-exceeded`, `upload-too-large`, `download-too-large` |
| stages past `max_staging_seconds` | the job `failed`, `staging-timed-out`, `limit: "max_staging_seconds"` |

### One gap: some Slurm interruptions read as `run-failed`

A job the scheduler loses ends `failed` with `run-interrupted`, as the contract
says, and each node it was running with it. So does a node whose image the
runtime could not pull, Docker's or a Slurm bundle's, and its job: `detail`
names the image, and the job-level `logs` the pull's error. A Docker
out-of-memory kill is `run-failed` with `detail` naming the memory limit, and a
node past its time limit names that. **Where `sc-server` falls short:** a node
ended by Slurm preemption or a `NODE_FAIL` ends `failed` with `run-failed`, as a
node whose tool failed does, and a Slurm `OUT_OF_MEMORY` is not named as a
memory limit. The contract is unchanged; this is `sc-server`'s gap.

### Credentials, as far as this profile has them

`client_credentials` assumes a confidential client with a real secret, and here
the secret is nominal: this profile borrows the grant's shape, not its
guarantees. DPoP applies in full, and that is what permits plaintext here
(identity §7).

### The refresh grace window is 300 seconds

The contract makes it a few minutes and leaves the value to the server. For 300
seconds after a refresh token is replaced, a repeat of it with a valid proof
from the session's own key gets a working pair whose refresh token is the
replacement already issued. After that the same repeat is reuse: the session
ends, and the token endpoint answers `invalid_grant`, `reason: "reused"`.

---

## 7. The key binding

A subject is bound to the first key that presents it, as best-effort
attribution, and another key presenting it is refused `invalid_client`. The
binding can be turned off only by code embedding the server
(`create_app(bind_keys=False)`), for a single trust domain such as a container
fleet, where `/etc/machine-id` is per image and every container derives the
same subject.

**Re-registration is not automatic**, even on a connection where the server
could verify the uid, such as a unix socket or loopback. A known subject
presenting a different key is refused wherever the request comes from, and the
operator's `release-binding` command is the one way back
([README, *The operator CLI*](README.md#the-operator-cli)).

**Pre-registration is not built.** An operator recording a user's key before
first contact would be the far end of the same switch, and would add no
endpoint and no refusal: an unknown subject would get the same `invalid_client`.
A deployment doing it would still publish `identity_assurance: "self_asserted"`,
since an operator vouching for a key still verifies nobody.
