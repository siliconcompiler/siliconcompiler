# What the pre-`v1` remote client did, and what the rewrite owes back

**Written 2026-09-22, immediately before `remote/client.py`, `remote/server.py` and their tests were
deleted.** The `v1` rewrite replaces both halves outright, so the wire changes and most assertions
are rewritten with it. **A behaviour that silently stops being asserted is how a rewrite loses
something**, and these tests were the only place these behaviours were written down.

**How to use this file:** every row is a behaviour a user could depend on. Tick it when the `v1`
client asserts the equivalent somewhere, or strike it and say why it no longer applies. **Phase 3's
gate is that no row is left untouched.** A row whose `v1` column reads *"gone"* still has to be a
deliberate answer, not an oversight.

---

## Where phase 3 left each section

**Signed off 2026-09-22, at the end of phase 3.** Every row below has an answer; this table is where
to look for it, and the four rows that are deliberately still open say so.

| | | |
|---|---|---|
| **A** job status | ✅ | `tests/remote/test_client_jobs.py`. A1 is `terminal`, A3 is `_record`, A6 became the node-state mapping, A8 is `_report_state`. **A4 and A5 are struck** — see below |
| **B** fetching results | ⏳ | **phase 4.** Nothing in this section is asserted yet, and `sc-remote` says so at the end of a run rather than leaving an empty build directory unexplained |
| **C** transport | ✅ | C1/C2 in `transport.py` (phase 2), C3–C7 in `test_client_jobs.py`, C8 is `delete_job`, C11–C13 were the phase-2 design requirements |
| **D** credentials | ✅ | phase 2 |
| **E** no server configured | ✅ | E4 is `test_an_unconfigured_client_refuses_before_it_packs_anything` — the test fails if the collection runs at all |
| **F** the CLI | ✅ | `tests/remote/test_parity.py`, against a live server. F7 and F8 are the reconnect path |
| **G** submit-time sanitation | ✅ | `runspec.normalize`, asserted end to end in `test_the_run_happens_inside_the_users_own_tree`. **G7 is struck** — see below |
| **I** the server entry point | ✅ | phase 1 |
| **H** not carried forward | ✅ | every one is gone, and the job path is what replaced H2, H3, H4 and H9 |

### The three rows that were struck rather than ticked

🔴 **A4 — elapsed time converted into a start time.** `v1` publishes `nodes[].started_at` and
`state_changed_at` as timestamps, so the derivation has nothing to derive. **What it bought survives
and is stronger**: the server records a node's start once, so a reconnect gets the same instant the
first connection did, where the old arithmetic restarted the clock at every poll.

🔴 **A5 — the `null` key is the setup manifest.** Gone with the protocol that had a magic node name.
`manifest` is an artifact kind, and phase 4 fetches it like any other.

🔴 **G7 — `scheduler.set_name(cluster)` on the submitted project.** **Struck, and it is the one
substantive change in the sanitation list.** The old server ran the flow in its own process and
dispatched each node to Slurm, holding a blocking `srun` per node for the length of the run. The job
is now the unit of submission: one `sbatch` for the whole flow, polled once per run, with the flow
inside it using SiliconCompiler's local scheduler. `-cluster` still names how a job is handed over —
it now names it to the *server*, not to the project. **That is what makes the API process something
other than a Slurm submit host, and it is the shape a `slurmrestd` transport swaps into.** The
consequence, stated: `-cluster docker` is no longer a choice the server CLI offers, because under
batch submission the container is the cluster's business.

Deleted in the same commit as this file was written:

| | |
|---|---|
| `siliconcompiler/remote/{client,server,schema}.py`, `remote/server_schema/` | the two halves |
| `siliconcompiler/apps/sc_server.py` | replaced by `python -m siliconcompiler.remote.server` |
| `tests/remote/{test_client,test_server}.py` | 2,969 lines |
| `tests/apps/test_sc_server.py` | |
| most of `tests/apps/test_sc_remote.py` | the two argument-shape tests stayed; they test the app wrapper, which is not being rewritten |
| the `scserver`, `scserver_users`, `scserver_nfs_path` fixtures in `tests/conftest.py` | `users.json` went with them |

---

## A. Reporting job status while a run is in flight

The client polled the server and turned the answer into log lines, `record,status` writes, and a
decision about whether to keep waiting. Under `v1` the poll is `GET /v1/jobs/{id}` with
`Retry-After` setting the pace, and node state comes from `nodes[]` with `terminal` published per
node — **so the parsing changes completely and every judgement below survives.**

| | Behaviour | `v1` equivalent |
|---|---|---|
| A1 | **A job with no running steps ends the wait loop.** No completed nodes, no start times, `running is False` | read `terminal` on the job object; **never switch on the state name** |
| A2 | **A status message the client cannot parse is reported, not crashed on.** `Job is still running: <whatever the server said>` and the loop continues | a body that is not the documented shape must not end the run |
| A3 | **Node statuses are recorded into `record,status`** for every node the server named | same, mapped from `nodes[].state` |
| A4 | 🔴 **Elapsed time is converted into a start time.** A node reporting `0:01:05` started 65 seconds ago. This is what makes the progress display's per-node timer continuous across a reconnect | `v1` publishes `state_changed_at` / `started_at` as timestamps, so the derivation goes away — **but the continuity it bought must not** |
| A5 | **The `null` key is the setup manifest**, and it is fetched like a node | `v1` has an explicit `manifest` artifact kind; it is no longer a magic node name |
| A6 | 🔴 **A node the client ran locally and uploaded reads back as `uploaded`, and counts as *pending* for this run** — not as complete. Without this the client treats its own uploads as finished work and never fetches them | the `uploaded` state has no `v1` node state. Decide what a locally-run node reads as, and keep it out of the terminal set |
| A7 | **A server that reports no timing still drives the loop.** Missing `elapsed_time` is not an error | absent is never an error; only `terminal` decides |
| A8 | **A status shared by more nodes than fit on a line is truncated with `...`**, and the count is in the label (`Success (12)`) | cosmetic, and the reason it exists is a 1000-node flow. Keep it |
| A9 | 🔴 **The client parsed what the server actually sent.** One test drove the real server's progress payload through the real client parser, so a change to one that the other could not read failed | **the conformance fixtures replace this**, and they are stronger: they are written from the contract rather than from whatever the server happens to emit |

## B. Fetching results

**This whole area is D13's rewrite, not a port.** Today the client fetches one `result.tar.gz` per
node and has one failure message for every way that can go wrong. Under `v1` results are a listing,
and a listing holding only the manifest is a **successful** run.

| | Behaviour | `v1` equivalent |
|---|---|---|
| B1 | **Results are downloaded, unpacked and merged into the local build tree**, landing at `build/<design>/<job>/<step>/<index>/outputs/` | same destination. The build directory is the thing a user actually looks at, and phase 3's gate is that it matches a local run |
| B2 | **The setup manifest is fetched as well as the nodes** | the manifest is an artifact kind, and **it may be the only one there is** |
| B3 | ⚠️ **A node with nothing to fetch is reported and does not derail the run** — `Could not fetch results for node: <node>` | 🔴 **one message becomes five sentences**: absent, blocked by an agreement, ungranted, deleted, expired. **Never say *expired* for a `deleted_at`** |
| B4 | **Downloads run in a `multiprocessing.Pool`**, one task per node, with an error callback | the pool is an implementation detail and may go. What may not is that one node's failure does not abort the others |

## C. Transport — what the client did with an unhappy server

🔴 **This is the area with the most carried-forward judgement and the least carried-forward code.**
Every row is a decision about *when to keep going*, and the `v1` client faces the same decisions
against a different vocabulary.

| | Behaviour | `v1` equivalent |
|---|---|---|
| C1 | **A timeout is retried rather than failing the job.** Three attempts in the recorded case | keep. `Retry-After` now sets the interval where the server supplies one |
| C2 | **Timeouts that never clear end the attempt** with `TimeoutError: Server communications timed out` — a bounded retry, not an infinite one | keep |
| C3 | **A redirected POST is followed**, because the spec turns the retry into a `GET` | 🔴 **`v1` uses `303` deliberately** for the artifact and log handovers. **Following a redirect is now load-bearing rather than a courtesy**, and the client branches on the served `Content-Type` at the target |
| C4 | **An error with no handler for it is surfaced**, as `Server responded with <code>: <message>` | becomes RFC 9457 rendering: what failed, the extension members that say which, and `trace_id` beside the page link |
| C5 | 🔴 **A non-JSON error body is reported as it came** — `Server responded with 502: Bad Gateway` | **this is the tolerance rule and it is now written down.** problem+json is promised only for what a *handler* produced, so `resp.json()["type"]` throws on exactly the errors production serves most. **A proxy's HTML `502` must render as something a person can act on** |
| C6 | 🔴 **A refusal ends the wait; a server error does not.** A `403` *job belongs to another user* stops polling and reports `refused`; a `500` is transient and the wait continues | keep the distinction exactly. Under `v1` the discriminator is the `type` slug, never the status alone |
| C7 | 🔴 **A refused poll ends the run as a failure, not as a finished job** — and the loop must not announce completion on the way out (no download pool is built) | keep. This is the difference between *your job failed* and *your job is done and empty* |
| C8 | **A job the server will not delete is an answer, not an exception.** `delete_job()` returns the body and logs `Unable to delete job: …` | `DELETE /v1/jobs/{id}` is idempotent and the job stays readable with `deleted_at` set |
| C9 | **The documented response shape is what the client returns** — `{'message': …, 'success': …}` | the shape changes; the principle that the client returns the server's answer rather than inventing one does not |
| C10 | ⚠️ **A plain-text body from an older server was accepted** as `{'message': <text>, 'success': True}` | 🔴 **gone, deliberately.** There is no legacy protocol in the `v1` client |
| C11 | 🔴 **Six `requests.post` sites, zero `headers=`** | **the design requirement**: one request path by construction, carrying `Authorization: DPoP` and a fresh proof |
| C12 | 🔴 **URLs were built with `urljoin(base, action)`** | **an anti-pattern to avoid on day one.** A base of `https://host/v1` loses the `/v1`. Join explicitly |
| C13 | 🔴 **The scheme was inferred from the port**, which itself defaulted to 443 — so a server on `:8000` was reached over plaintext | **gone.** The scheme comes from the URL. This bit every compose rig |

## D. Configuration and credentials

`sc-remote -configure` is where a login goes, and it is the one command the eventual `sc-config`
rename touches. **The file's location and its mode are a shipped security fix (#5235, v0.38.4) and
may not regress.**

| | Behaviour | `v1` equivalent |
|---|---|---|
| D1 | 🔴 **The credentials file is written `0600`**, and a pre-existing `0644` file is **tightened** on rewrite. Asserted on both the create and the update path, and on the whitelist rewrite too, which rewrites the whole file | **must not regress.** A DPoP private key raises the stakes rather than lowering them |
| D2 | **Every answer supplied means no prompt**, so a scripted run needs no terminal | keep. CI has no tty |
| D3 | **An existing configuration is not overwritten on a guess** — `clobber=True`, or an interactive `y` | keep |
| D4 | **Declining the overwrite prompt writes nothing** | keep |
| D5 | **An unanswerable prompt is an error, not a silent no-op** — `choose a server address` / `a remote server address is required`, and **no file is written** | keep. There is no default server to fall back on |
| D6 | **Credentials may be embedded in the address** — `https://user:pass@example.com` splits into `address`, `username`, `password`; `:@example.com` yields neither | ⚠️ **username/password stop being the credential.** Decide whether the address still carries anything |
| D7 | **A port in the address is split out** — `https://example.com:1234` → `address` + `port: 1234` | keep the parse; **do not re-derive the scheme from the result** (C13) |
| D8 | **Unsupplied credentials are simply absent** from the file, not written empty | keep |
| D9 | **Whitelist entries are added once (no duplicates) and can be removed**; removing something never listed is not an error | keep. The whitelist is what bounds what gets uploaded |
| D10 | **The configuration in use is reportable** — `print_configuration()` prints the server, the username and the directory whitelist | keep, with the DPoP key thumbprint as the new thing worth showing |
| D11 | ⚠️ **`accept_terms` is a deprecated, ignored parameter that warns** | the shim may go with the rewrite. **The behaviour the contract objected to is already removed** |
| D12 | ✅ **Terms the *server* advertises are still rendered** | 🔴 **keep the mechanism.** `sc-server` sends `terms: []`, but the contract's scoped `terms` list needs exactly this |

## E. No server configured — four tests that stop being an edge case

🔴 **`default_server` was removed in [#5423](https://github.com/siliconcompiler/siliconcompiler/pull/5423)
(merged 2026-09-22, unreleased, a declared breaking change).** These four were written for a case
that is now **the normal one**, so they are the behaviour to carry forward rather than rewrite.

| | Behaviour | `v1` equivalent |
|---|---|---|
| E1 | **A client with no configuration still constructs.** It logs `Could not find remote server configuration` and its URL is `None` | keep. Constructing must not raise |
| E2 | **A missing address is reported as such** — `Server: not configured`, never a server named `None` | keep |
| E3 | **A request with no address names the way to fix it** — `No remote server address is configured` | keep |
| E4 | 🔴 **The job is refused *before* its build directory is collected and packed up.** The test fails if `__run_preprocess` runs at all | **keep, and it matters more under `v1`**: the three-call submit means there is more to waste |

## F. The `sc-remote` CLI

**`apps/sc_remote.py` is not being rewritten** — 176 lines of argument shape over a 1,139-line
client. Two tests stayed with it; the rest tested the client through it and are captured above.

| | Behaviour | `v1` equivalent |
|---|---|---|
| F1 | ✅ **`-configure`, `-reconnect`, `-cancel` and `-delete` are mutually exclusive**, exit `1` | **kept in `tests/apps/test_sc_remote.py`** |
| F2 | ✅ **`-reconnect`, `-cancel` and `-delete` require `-cfg`**, exit `2` | **kept in `tests/apps/test_sc_remote.py`** |
| F3 | **A blank address at the `-configure` prompt exits `3`** and writes no file | the app maps the client's `ValueError` to an exit code; keep both halves |
| F4 | **`-configure -list` prints the configuration and exits `0`** | keep |
| F5 | **`-cancel` / `-delete` call `check()` first**, then the verb | keep the order: the client confirms the server before acting on it |
| F6 | **A bare `-cfg` reports the job's status** and exits `0` | keep |
| F7 | 🔴 **`-reconnect` re-enters the wait loop for a job already running**, re-deriving which nodes to fetch from the flow's entry nodes, and calls `summary()` at the end | keep. **This is the answer to Ctrl+C** and the only way back to a detached job |
| F8 | **Ctrl+C on a remote run prints the commands to get back to it** — `To reconnect to this job use: sc-remote -cfg …` and `To cancel this job use: …` | 🔴 **keep verbatim in spirit.** A user who interrupts a long run needs the job id and two commands, not a traceback |
| F9 | **An absent `-cfg` manifest is an error with the path in it**, exit `1` | keep |

## G. Submit-time sanitation — the seven settings the server applied

🔴 **This list *is* the sanitation policy**, and it survives the code that held it. It was applied at
`server.py:334-382`, **and three of the seven were applied a second time at `:801-803` with the two
copies disagreeing** — which is the duplication [shared-project-setup.md] names, and also why
*"two spellings of the same setup are two hashes of the same job"* is the run hash's precondition.

**Under `v1` this happens once, at `POST /v1/jobs/{id}/submit`, after the digest check and after the
archive limits bind.**

| | Setting | Why it is there |
|---|---|---|
| G1 | `option.set_nodashboard(True)` | there is no terminal on the server |
| G2 | `option.set_builddir(<job root>)` | 🆕 **now `<datadir>/users/<user_id>/builds/<job_id>/`** — per user as well as per job |
| G3 | `option.set_cachedir(<cache>)` | 🆕 **now `<datadir>/users/<user_id>/cache/`.** Was deliberately cluster-wide, *"cluster-wide rather than per-job — under `job_root` every job would re-download the PDK"*. **The per-user cost is accepted**; it is what makes the tree single-owner and fixes the `ccache`/`coursier` `EPERM` and the owner-only dataroot sweep together |
| G4 | `option.set_remote(False)` | 🔴 **without it the compute node tries to submit the job again.** The one setting whose absence is an infinite loop |
| G5 | `option.set_nodisplay(True)` | no display on a compute node |
| G6 | `option.set_quiet(True)` | the server's own logging is the record |
| G7 | `scheduler.set_name(cluster)` **when it is not `local`** | `local` already means *unset*; any other value names the per-node scheduler |
| G8 | `set('record', 'remoteid', <hash>)` | 🆕 **now the server-owned job id, and a UUIDv7** rather than `uuid.uuid4().hex`, so a user's ids sort by when they ran |

## I. The server's own entry point degrades without its extra

🔴 **The console script was installed whether or not the `server` extra was**, so the command line
had to work without it. **The same is true of `python -m siliconcompiler.remote.server`**, and the
extra is now `flask` rather than `aiohttp`.

| | Behaviour | `v1` equivalent |
|---|---|---|
| I1 | 🔴 **`-h` works with the extra missing** and exits `0` | **keep.** ⚠️ **The docs build renders the apps reference from this**, so losing it fails the docs gate rather than a test |
| I2 | **Actually starting the server without the extra prints a message and exits `1`** — `sc-server is unavailable: …` plus `pip install "siliconcompiler[server]"` — **never a traceback** | keep, reworded for the module entry point |
| I3 | **`Server().run()` raises `ModuleNotFoundError` naming the install command** when called as a library | keep |
| I4 | **An unrecognised option exits non-zero** rather than being ignored | keep |

## H. Deliberately not carried forward

Each of these is a half-shaped version of something the contract now specifies properly. **They are
removals, not migrations** — do not port any of them.

| | | Replaced by |
|---|---|---|
| H1 | `users.json`, read once at startup | the `users`, `devices` and `token_families` tables |
| H2 | **The `.owner` file inside the job's own build directory** | `jobs.user_id`. The access-control record no longer lives in the thing it protects |
| H3 | **The in-process job dict**, emptied in a `finally` when the job ends | the `jobs` table. The server can now answer *what did I run yesterday?* |
| H4 | **`__job_belongs_to()` returning `True` for everyone** ([#5288](https://github.com/siliconcompiler/siliconcompiler/pull/5288)) | 🔴 **a real owner predicate on every read and write.** This is the defect the identity work exists to fix |
| H5 | **The client's own quota arithmetic** — `time_remaining` computed from fields the server never enforced | `GET /v1/me`'s `usage`, which the server does act on |
| H6 | **`-auth`, `users.json` passwords, and the whole authenticated/unauthenticated fork** | one path: `client_credentials` + DPoP, with the key bound on first contact |
| H7 | **`-maxuploadsize` in MB** | `limits.max_upload_bytes`, in bytes, published at `GET /v1` and refused with `upload-too-large` naming the key |
| H8 | **`-checkinterval`** | `Retry-After`, set by the server per response |
| H9 | **The RPC verbs** — `/remote_run/`, `/check_progress/`, `/check_server/`, `/get_results/`, `/cancel_job/`, `/delete_job/` | the 18 endpoints of the `sc-server` profile |

---

## Notes taken while a phase had two things in view at once

**These are decisions recorded where they were cheap to make, for work that
happens elsewhere.** Each names what it is for, so a later phase does not
re-derive it.

### The Slurm JWT surface is the identity surface (phase 2, for the REST follow-on)

🔴 **`slurmrestd` over TCP needs `AuthAltTypes=auth/jwt` and a JWT key, and that
is the same JWT machinery the identity work already reasons about** — so they
are decided together rather than twice. `slurm.conf.in` sets no `AuthAltTypes`
at all today; the stack is pure munge, which authenticates only callers sharing
the munge key.

⚠️ **The alternative — a local UNIX socket under munge — only helps a client
already on the controller host**, which is precisely the shape the REST work
exists to escape: it is what lets the API server and `slurmctld` be separate
containers.

✅ **What this server already does that the follow-on needs:** it holds a
signing secret at `<datadir>/token-signing-key`, 0600, created on first start.
A Slurm JWT key is the same kind of object with the same handling, and
`slurmrestd` **does not need the key itself** — it forwards the caller's token
and `slurmctld` verifies it, so the key stays `0600 slurm:slurm`.

🔴 **Pin `data_parser` to `v0.0.41`.** Valid through 25.11.8, gone at 26.05.4.

### Dispatch is batch-submit-and-poll (phase 1, for the job path)

**`slurmrestd` submits batch jobs only** — there is no `srun` over REST — so
`sbatch` and REST are one design with two transports rather than two designs.
What would make them two is writing today's shape: one blocking `srun` per
node, held by the client.

🔴 **So the job path writes: submit a batch job, record `scheduler_job_id`,
poll, read the log off the shared filesystem.** ⚠️ **Poll once per run over the
job list, never once per node** — every REST request is one or more RPCs into
`slurmctld`, and a per-node poll at N-wide fan-out is the traffic
`--max-connections` exists to throttle.

The seam that matters is **not** a `Dispatcher` base class with one
implementation. It is that nothing in the job model assumes the API process is
a Slurm submit host: `jobs.scheduler_job_id` is already just text, and dispatch
lives in one module.
