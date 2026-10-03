-- The v1 store: 20 tables of the contract's 42.
--
-- Every table's shape is the contract's; the engine and the subset differ.
-- sc-server is the unauthenticated profile plus the image registry, so
-- entitlements, terms, projects, the artifact gate, the admin tables and
-- metering are absent, and each foreign key they take with them is noted.
--
-- Postgres to SQLite:
--   uuid          -> text, the canonical hyphenated form of a UUIDv4
--   timestamptz   -> text, RFC 3339 in UTC ('2026-09-22T11:22:33.456Z')
--   jsonb         -> text holding JSON; the JSON1 functions read it in place
--   boolean       -> integer constrained to 0 or 1
--   bigserial     -> integer primary key, which SQLite aliases to the rowid
--   inet, char(32)-> text
--   now()         -> strftime, so a default and a Python write agree on format
--
-- `index` is a SQLite keyword, so that node column is always quoted. Foreign
-- keys are enforced only under `PRAGMA foreign_keys = ON`, which store.py sets.

PRAGMA foreign_keys = ON;


CREATE TABLE users (
    id              text PRIMARY KEY,               -- opaque; this is the JWT `sub`
    issuer          text NOT NULL,                  -- 'local' for an auto-provisioned identity,
                                                    -- so a real IdP later cannot collide with one
    subject         text NOT NULL,                  -- the machine-id+uid derivation when
                                                    -- issuer='local'; an IdP's immutable sub
                                                    -- otherwise, never the email
    email           text,                           -- mutable: displayed, never joined on
    hd              text,
    display_name    text,
    posix_account   text UNIQUE,                    -- the Slurm mapping; NULL until provisioned
    role            text NOT NULL DEFAULT 'user'
                        CHECK (role IN ('user', 'admin')),
                                                    -- nothing reads it (everyone is an admin
                                                    -- here); kept for one shape with crucible
    created_at      text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_seen_at    text,
    deactivated_at  text,                           -- active is deactivated_at IS NULL
    UNIQUE (issuer, subject)
);
CREATE UNIQUE INDEX users_email_key ON users (lower(email)) WHERE email IS NOT NULL;


CREATE TABLE devices (
    id                 text PRIMARY KEY,
    user_id            text NOT NULL REFERENCES users(id),
    name               text NOT NULL,               -- renamed in the portal; no API endpoint
    dpop_jkt           text NOT NULL,               -- JWK thumbprint: THIS is the pin, the only
                                                    -- real control where identity is unverified
    machine_id_hash    text,                        -- a label, deliberately NOT unique.
                                                    -- NULL when nothing could be derived
    machine_id_source  text NOT NULL CHECK (machine_id_source IN
                         ('linux_machine_id', 'macos_platform_uuid',
                          'windows_machine_guid', 'none')),
    enrolled_at        text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_seen_at       text,
    revoked_at         text
);
CREATE INDEX devices_user_idx ON devices (user_id) WHERE revoked_at IS NULL;
-- Partial, not a column constraint: a revoked device keeps its thumbprint, and
-- the same machine may enrol again with a fresh key.
CREATE UNIQUE INDEX devices_dpop_jkt_idx ON devices (dpop_jkt) WHERE revoked_at IS NULL;

CREATE TABLE device_events (                        -- append-only
    id          integer PRIMARY KEY,
    device_id   text NOT NULL REFERENCES devices(id),
    kind        text NOT NULL CHECK (kind IN
                  ('enrolled', 'machine_id_mismatch', 'reauth_succeeded',
                   'reauth_failed', 'revoked',
                   'authorization_approved', 'authorization_denied')),
    actor_id    text REFERENCES users(id),          -- the human, where there was one
    occurred_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    remote_addr text,
    detail      text                                -- JSON
);
CREATE INDEX device_events_device_idx ON device_events (device_id, occurred_at DESC);

CREATE TABLE token_families (
    id                  text PRIMARY KEY,           -- the `family` claim
    user_id             text NOT NULL REFERENCES users(id),
    device_id           text REFERENCES devices(id),
    kind                text NOT NULL CHECK (kind IN ('interactive', 'ci')),
                                                    -- the contract's closed vocabulary; only
                                                    -- 'interactive' is written here. CI is
                                                    -- crucible's, so ci_credential_id is absent
    dpop_jkt            text NOT NULL,              -- the bound key, checked on every refresh
    scope               text NOT NULL,              -- the CEILING, space-delimited and ALREADY
                                                    -- EXPANDED ('jobs:read jobs:write'). A
                                                    -- rotation may narrow inside it, never widen
    created_at          text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    expires_at          text NOT NULL,              -- the session's end: set at creation, NEVER
                                                    -- extended by a refresh or by activity
    revoked_at          text,
    revoked_reason      text CHECK (revoked_reason IN
                          ('user_logout', 'reuse_detected', 'device_revoked',
                           'ci_credential_revoked', 'account_inactive', 'admin')),
    CHECK (kind <> 'ci' OR device_id IS NULL)
);
CREATE INDEX token_families_user_idx ON token_families (user_id) WHERE revoked_at IS NULL;
CREATE INDEX token_families_device_idx ON token_families (device_id) WHERE revoked_at IS NULL;

CREATE TABLE refresh_tokens (
    jti          text PRIMARY KEY,
    family_id    text NOT NULL REFERENCES token_families(id),
    issued_at    text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    expires_at   text NOT NULL,                     -- CLAMPED to the family's expires_at
    revoked_at   text,
    replaced_by  text REFERENCES refresh_tokens(jti),
    replaced_at  text
);
CREATE INDEX refresh_family_idx ON refresh_tokens (family_id);


CREATE TABLE job_states (                           -- the closed set, as a table
    state    text PRIMARY KEY,
    terminal integer NOT NULL CHECK (terminal IN (0, 1))
);
INSERT INTO job_states VALUES
    ('created', 0), ('awaiting_input', 0),
    ('staging', 0),             -- fetching the sources it does not hold, before it
                                -- queues. The one edge back leaves from here
    ('queued', 0), ('running', 0),
    ('cancelling', 0),          -- cancel accepted, run not yet stopped
    ('completed', 1), ('failed', 1), ('cancelled', 1),
    ('rejected', 1),            -- refused at submit; it never ran
    ('abandoned', 1);           -- the upload never arrived and the grant expired

CREATE TABLE node_states (                          -- a NODE's closed set. Not job_states
    state    text PRIMARY KEY,
    terminal integer NOT NULL CHECK (terminal IN (0, 1))
);
INSERT INTO node_states VALUES
    ('pending', 0),             -- admitted, not yet dispatched
    ('queued', 0),              -- with the scheduler
    ('preparing', 0),           -- dispatched, fetching its image: minutes, which
                                -- would otherwise look like a hang
    ('running', 0),
    ('completed', 1), ('failed', 1),
    ('skipped', 1),             -- deliberately not run: a condition, a cached hit
    ('cancelled', 1);           -- the job ended before this node started

CREATE TABLE jobs (
    id                text PRIMARY KEY,             -- one opaque id, not the content hash
    user_id           text NOT NULL REFERENCES users(id),
                                                    -- project_id absent: no 'projects' feature
    device_id         text REFERENCES devices(id),  -- which machine submitted it

    state             text NOT NULL REFERENCES job_states(state),
    state_changed_at  text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                                                    -- PUBLISHED under this same name, written
                                                    -- on every transition

    design            text NOT NULL,
    jobname           text NOT NULL,
    manifest_flow     text,                         -- which flowgraph ran, re-derived at submit

    descriptor        text NOT NULL,                -- JSON: POST /v1/jobs exactly as asserted
    manifest_node_count integer,                    -- re-derived at submit
    manifest_tools    text,                         -- JSON, re-derived at submit
    manifest_pdk      text,                         -- re-derived at submit: a PDK name, or the
                                                    -- literal 'none' = this flow requires no PDK
    manifest_resources text,                        -- JSON [[kind, name], ...], re-derived at
                                                    -- submit: the PDKs and libraries the run
                                                    -- uses, which a continuing job takes on (D175)

    upload_storage_key      text,                   -- the object key the grant was issued for
    upload_location_id      text REFERENCES storage_locations(id),
    upload_digest           text,                   -- 'sha256:<hex>', asserted at submit and
                                                    -- verified against what storage reports
    upload_size_bytes       integer,
    upload_grant_expires_at text,                   -- also the reaper's trigger
    upload_revoked_at       text,
    grant_bytes             integer,                -- the size the FIRST grant of the archive
                                                    -- now being uploaded fixed; a re-issue
                                                    -- must repeat it. NULL between archives
    grant_digest            text,                   -- the digest that grant bound beside it;
                                                    -- submit runs only bytes matching it
    archives_bytes          integer NOT NULL DEFAULT 0,
                                                    -- every archive this job has consumed,
                                                    -- together: max_upload_bytes bounds the sum
    upload_sources          text,                   -- JSON: what the server is ASKING for, in
                                                    -- created or awaiting_input. NULL otherwise
    python_packages         text,                   -- JSON: the create body's python_packages
                                                    -- as accepted, the builder's input (database
                                                    -- D147). NULL where the job lists none
    python_answered         text,                   -- JSON: each distribution this job was sent
                                                    -- back for, by canonical name; its wheel
                                                    -- replaces the entry and alone may overlap

    create_idempotency_key text,                   -- written with the row, so a refused create,
                                                    -- which writes none, binds no key
    submit_idempotency_key text,
    create_reply      text,                         -- JSON: the create's original body, replayed
    submit_reply      text,                         -- JSON: the submit's original body, replayed
    submit_key_at     text,                         -- when submit_idempotency_key was bound
    unpack_pending    integer NOT NULL DEFAULT 0,   -- 1 from submit until staging unpacks
                                                    -- the newest upload
    run_hash          text,                         -- the client's opaque hash of the work, never
                                                    -- recomputed. Safe to trust because reuse is
                                                    -- owner-scoped: a wrong hash hands a user
                                                    -- their own stale job
    job_identity      text,                         -- H(run_hash || the digests this job's
                                                    -- declared versions resolved to): what reuse
                                                    -- is keyed on, so re-registering an image
                                                    -- invalidates reuse exactly when it should
    image_id          text REFERENCES images(id),   -- the container this job's own process runs
                                                    -- in, from requested_versions.python alone
                                                    -- (D145). NULL where no containers run
    scheduler_job_id  text,                         -- set only where the JOB is the unit of
                                                    -- submission; per-node dispatch puts it on
                                                    -- job_nodes instead. At most one level
    submit_trace_id   text CHECK (submit_trace_id IS NULL OR length(submit_trace_id) = 32),
    error_type        text,                         -- the RFC 9457 `type` URI
    error_members     text,                         -- JSON: the type's own members of the job's
                                                    -- `error`; its `detail` is the transition's
                                                    -- reason. NULL when error_type is NULL
    state_reason      text,                         -- display only: the staging phase, or a
                                                    -- cancel's reason. Bounded and scrubbed

    created_at        text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    submitted_at      text,
    started_at        text,
    finished_at       text,
    cancel_requested_at text,
    archived_at       text,                         -- VIEW ONLY: the job leaves the default list
                                                    -- and is unchanged in every other respect
    archived_by       text REFERENCES users(id),
    deleted_at        text,                         -- the job stays readable after DELETE, its
                                                    -- subresources 404. Not a `deleted` state,
                                                    -- which would erase how the job ended
    deleted_by        text REFERENCES users(id),
    deleted_reason    text,                         -- prose naming who acted, never the device

    -- A job that was queued has a resolved PDK. Staging re-derives the
    -- manifest, so a staging, cancelling or failed job can lack one (database
    -- D129, reversing D100).
    CONSTRAINT jobs_admitted_pdk_resolved
        CHECK (state NOT IN ('queued', 'running', 'completed')
               OR (manifest_pdk IS NOT NULL AND manifest_pdk <> '')),
    -- Only a job that has stopped may be archived. The terminal five are spelled
    -- out because a CHECK cannot read job_states.terminal.
    CONSTRAINT jobs_archived_is_terminal
        CHECK (archived_at IS NULL
               OR state IN ('completed', 'failed', 'cancelled', 'rejected', 'abandoned')),
    CHECK ((archived_at IS NULL) = (archived_by IS NULL)),
    CHECK ((deleted_at IS NULL) = (deleted_by IS NULL))
);
CREATE UNIQUE INDEX jobs_create_idempotency_idx ON jobs (user_id, create_idempotency_key)
    WHERE create_idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX jobs_submit_idempotency_idx ON jobs (user_id, submit_idempotency_key)
    WHERE submit_idempotency_key IS NOT NULL;
-- This index IS the published ordering of GET /v1/jobs: created_at DESC, the
-- opaque id a bytewise tiebreaker, ?cursor= a keyset over that pair. The partial
-- predicate is why a deleted job leaves the list.
CREATE INDEX jobs_list_idx ON jobs (user_id, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NULL;
-- ?archived=true: the SAME ordering over the complement. Two partial indexes, so
-- the default list, the hot path, carries none of the archive's rows.
CREATE INDEX jobs_archived_idx ON jobs (user_id, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NOT NULL;
CREATE INDEX jobs_design_idx ON jobs (user_id, design, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NULL;
CREATE INDEX jobs_jobname_idx ON jobs (user_id, jobname, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NULL;
CREATE INDEX jobs_concurrent_idx ON jobs (user_id)
    WHERE state IN ('staging', 'queued', 'running', 'cancelling');   -- staging too:
                                                    -- fetches are work
CREATE INDEX jobs_pending_idx ON jobs (user_id) WHERE state IN ('created', 'awaiting_input');
-- Owner-scoped, per the reuse rule, and partial. On job_identity, not run_hash:
-- the same work resolved to different images is a different job.
CREATE INDEX jobs_run_hash_idx ON jobs (user_id, job_identity)
    WHERE job_identity IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE job_state_transitions (                -- append-only
    id            integer PRIMARY KEY,
    job_id        text NOT NULL REFERENCES jobs(id),
    from_state    text REFERENCES job_states(state),
    to_state      text NOT NULL REFERENCES job_states(state),
    actor_id      text REFERENCES users(id),        -- the person who caused it. NULL = the
                                                    -- scheduler, the worker or the reaper
                                                    -- elevation_id absent: no admin mode here
    occurred_at   text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    reason        text,
    trace_id      text CHECK (trace_id IS NULL OR length(trace_id) = 32)
                                                    -- the trace this transition HAPPENED IN, not
                                                    -- the request that caused it: most have none
);
CREATE INDEX job_transitions_job_idx ON job_state_transitions (job_id, occurred_at);

CREATE TABLE job_nodes (
    job_id      text NOT NULL REFERENCES jobs(id),
    step        text NOT NULL,                      -- 'place'
    "index"     text NOT NULL,                      -- '0' -- a name, not a number
    state       text NOT NULL REFERENCES node_states(state),
    image_id    text REFERENCES images(id),         -- the container THIS NODE ran in, written at
                                                    -- dispatch. NULL = never dispatched
    scheduler_job_id text,                          -- the scheduler id for THIS NODE, written at
                                                    -- dispatch beside image_id; what a cancel and
                                                    -- the reconciling sweep resolve
    started_at  text,
    finished_at text,
    exit_code   integer,
    error_type  text,                               -- the same taxonomy as jobs.error_type
    error_members text,                             -- JSON: the rest of the node's `error`:
                                                    -- `detail` and the type's own members.
                                                    -- NULL when error_type is NULL
    state_reason text,                              -- display only: a cancel's reason
    metrics     text,                               -- JSON: what the node's portal panel shows,
    records     text,                               -- from the run's final manifest read ONCE as
                                                    -- plain JSON when the job ends, never through
                                                    -- SiliconCompiler (contract §1). NULL before
    PRIMARY KEY (job_id, step, "index")
);
CREATE INDEX job_nodes_scheduler_idx                -- the sweep's direction is id -> node
    ON job_nodes (scheduler_job_id) WHERE scheduler_job_id IS NOT NULL;

CREATE TABLE job_node_edges (                       -- the flow's shape, as rows, so a page can
    job_id     text NOT NULL,                       -- draw the DAG without reading object storage
    from_step  text NOT NULL,
    from_index text NOT NULL,
    to_step    text NOT NULL,
    to_index   text NOT NULL,
    PRIMARY KEY (job_id, from_step, from_index, to_step, to_index),
    FOREIGN KEY (job_id, from_step, from_index) REFERENCES job_nodes (job_id, step, "index"),
    FOREIGN KEY (job_id, to_step,   to_index)   REFERENCES job_nodes (job_id, step, "index")
);

CREATE TABLE job_continuations (                    -- a run starting part-way (surface D175):
    job_id      text NOT NULL REFERENCES jobs(id),  -- per node it reads and does not run, the job
    step        text NOT NULL,                      -- whose results were copied in, written at
    "index"     text NOT NULL,                      -- create. The key demands the job that RAN
    from_job_id text NOT NULL,                      -- the node; the handler checks it completed
    PRIMARY KEY (job_id, step, "index"),
    FOREIGN KEY (from_job_id, step, "index") REFERENCES job_nodes (job_id, step, "index"),
    CHECK (from_job_id <> job_id)
);


CREATE TABLE artifact_kinds (                       -- the vocabulary, and how long each kind is
    kind              text PRIMARY KEY,             -- kept. retention_seconds is a floor that is
    retention_seconds integer                       -- READ. NULL = the floor and nothing more
                        CHECK (retention_seconds IS NULL OR retention_seconds > 0)
);
INSERT INTO artifact_kinds (kind, retention_seconds) VALUES
    ('manifest', 157680000), -- five years. What the run WAS: small, and wanted later
    ('logs',     157680000),
    ('reports',  157680000),
    ('issue',    157680000), -- a failure is what you come back to
    ('final',    157680000), -- the deliverables. Re-making one is a re-run
    ('outputs',  NULL),      -- large, regenerable, and the most sensitive: the floor, no more
    ('input',    NULL),      -- what went IN: each uploaded archive, job-level, and
                             -- a node's inputs/ bound to the node
    ('node',     NULL),      -- one node's whole working directory, never outliving its
                             -- contents. ALWAYS bound to a node: no job-level tarball
    ('staging',  157680000), -- the server's record of the job, for its submitter, from create
                             -- to dispatch: a section each time it stages. Kept as logs are
    ('diagnostics', 7776000); -- 90 days. The operators' record, unscrubbed: read when
                             -- something went wrong recently, and never over the API
-- Starting values. The numbers are the deployment's; the SHAPE is the contract.
-- The set is CLOSED and PUBLISHED, so a new value is a version bump.

CREATE TABLE storage_locations (                    -- WHERE 'where' is
    id       text PRIMARY KEY,                      -- 'primary', 'archive-2026'
    uri_base text NOT NULL,                         -- 'file:///srv/artifacts/', read to build a
                                                    -- URL. A URI, so file:// is first-class
    writable integer NOT NULL DEFAULT 1 CHECK (writable IN (0, 1))
                                                    -- false after a migration: still read, never
                                                    -- written to again. SEVERAL may be writable
);

CREATE TABLE artifacts (
    id            text PRIMARY KEY,
    job_id        text NOT NULL REFERENCES jobs(id),
    step          text,                             -- 'place'; NULL for job-level artifacts
    "index"       text,                             -- '0'; NULL for job-level artifacts
    digest        text NOT NULL,                    -- WHAT the bytes are: 'sha256:<hex>'. The
                                                    -- integrity and dedup identity, published
    location_id   text NOT NULL REFERENCES storage_locations(id),
    storage_key   text NOT NULL,                    -- WHERE in it. Never on the wire, and MAY be
                                                    -- shared between rows
    size_bytes    integer NOT NULL,
    media_type    text,
    kind          text NOT NULL REFERENCES artifact_kinds(kind),
    upload_seq    integer,                          -- 1, 2, ... for a job-level 'input': which
                                                    -- upload it was. NULL on every other row
    created_at    text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    retained_until text,                            -- published under the same name: a floor,
                                                    -- not a deletion time
    provenance    text NOT NULL DEFAULT 'unknown'
                    CHECK (provenance IN
                      ('pending',                   -- being described -- NEVER fetchable
                       'declared',                  -- described
                       'unknown')),                 -- nobody will
    legal_hold_at     text,                         -- SET = held: effectively undeletable
    legal_hold_by     text REFERENCES users(id),
    legal_hold_reason text,
    withheld_at   text,                             -- server-side suppression. Lowers the derived
    withheld_by   text REFERENCES users(id),        -- policy, never raises it
    withheld_reason text,
    deleted_at    text,                             -- THE BYTES ARE GONE. The row stays.
    deleted_by    text REFERENCES users(id),        -- NULL deleted_by = the reaper; set = a
    deleted_reason text,                            -- person, who owes a reason
    CHECK (("index" IS NULL) = (step IS NULL)),     -- both, or neither. Deliberately NOT a
                                                    -- foreign key into job_nodes
    CHECK ((upload_seq IS NOT NULL) = (kind = 'input' AND step IS NULL)),
    CHECK (upload_seq IS NULL OR upload_seq >= 1),
    CHECK (legal_hold_at IS NULL
        OR (legal_hold_by IS NOT NULL AND legal_hold_reason IS NOT NULL)),
    CHECK ((withheld_at IS NULL) = (withheld_by IS NULL)),
    CHECK (NOT (legal_hold_at IS NOT NULL AND deleted_at IS NOT NULL)),
    CHECK (deleted_at IS NOT NULL OR (deleted_by IS NULL AND deleted_reason IS NULL)),
    CHECK (deleted_by IS NULL OR deleted_reason IS NOT NULL)
);
CREATE INDEX artifacts_live_digest_idx ON artifacts (digest) WHERE deleted_at IS NULL;
CREATE INDEX artifacts_job_idx ON artifacts (job_id);
CREATE INDEX artifacts_node_idx ON artifacts (job_id, step, "index");
CREATE INDEX artifacts_digest_idx ON artifacts (digest);
-- What reclaiming bytes counts: an object is its location and its key, and it
-- is only unlinked when no live row names the pair.
CREATE INDEX artifacts_live_object_idx ON artifacts (location_id, storage_key)
    WHERE deleted_at IS NULL;

-- One row per kind per node, and it has to be the DATABASE that says so:
-- indexing runs from reconcile on whichever request thread gets there first,
-- and two writers that check before inserting can both pass.
-- coalesce because SQLite counts NULLs as distinct in a unique index, which
-- would leave the job-level rows unprotected. `upload_seq` makes a job-level
-- `input` one per UPLOAD rather than exempt (database D101).
CREATE UNIQUE INDEX artifacts_one_per_node_idx
    ON artifacts (job_id, kind, coalesce(step, ''), coalesce("index", ''),
                  coalesce(upload_seq, 0));


CREATE TABLE software (                             -- what this deployment knows how to run
    name          text PRIMARY KEY,                 -- the DISTRIBUTION name, and the wire key:
                                                    -- 'siliconcompiler', 'openroad'
    display_name  text NOT NULL,
    kind          text NOT NULL                     -- which bucket it is published in, and which
                    CHECK (kind IN                  -- question the resolution asks about it
                      ('python',                    -- a distribution in the interpreter. The whole
                                                    -- python set is satisfied by ONE image,
                                                    -- because they share a process
                       'tool',                      -- an executable. Satisfied PER NODE, by an
                                                    -- image holding the python set and this tool
                       'interpreter')),             -- 'python': the image's own Python, which
                                                    -- the probe reads. Satisfied by each image a
                                                    -- node running the user's Python resolves to
                                                    -- Derived and never typed: the mechanism
                                                    -- that reads the version IS the
                                                    -- classification (see probe.py)
    driver        text,                             -- the module carrying this tool's Task driver:
                                                    -- 'siliconcompiler.tools.openroad'. NULL for a
                                                    -- python distribution, and for a tool nobody
                                                    -- here drives.
                                                    -- RECORDED, not derived: a driver may live
                                                    -- in any package, and even in-tree
                                                    -- 'kepler-formal' is ...tools.keplerformal.
                                                    -- Filled in by a scan at registration
    version_package text,                           -- read this tool's version from a PYTHON
                                                    -- distribution of this name instead of by
                                                    -- running it: 'pyslang' for the tool 'slang'.
                                                    -- A tool may have no executable and still
                                                    -- need an image holding it; recorded, since
                                                    -- the names differ
    added_at      text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    added_by      text NOT NULL REFERENCES users(id),
    retired_at    text,
    retired_by    text REFERENCES users(id),
    CHECK (length(name) <= 100),
    -- A task driver is what makes something a tool. The reverse is allowed: a
    -- tool nobody here drives reports no version, which `published_date` is for.
    CHECK (driver IS NULL OR kind = 'tool'),
    -- A python distribution's own name IS where its version comes from, so this
    -- would be a second source there.
    CHECK (version_package IS NULL OR kind = 'tool'),
    CHECK ((retired_at IS NULL) = (retired_by IS NULL))
);

CREATE TABLE software_versions (                    -- which versions of it, and in what order
    software_name text NOT NULL REFERENCES software(name),
    version       text NOT NULL,                    -- exact, normalised to PEP 440 at
                                                    -- registration. STORAGE has no ranges: the
                                                    -- wire's specifiers are matched against it
    version_source text NOT NULL DEFAULT 'reported' -- where the number came from
                     CHECK (version_source IN
                       ('reported',                 -- the tool said so. The ONLY kind that can
                                                    -- satisfy a version requirement
                        'published_date')),         -- it said nothing, so the image's publish
                                                    -- date. Marked, since 20260924 beats 2.0.1
                                                    -- under every comparison: it never satisfies
                                                    -- a requirement and sorts BELOW a reported one
    preference    integer NOT NULL DEFAULT 0,       -- orders GET /v1's array; higher first
    added_at      text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    added_by      text NOT NULL REFERENCES users(id),
    retired_at    text,
    retired_by    text REFERENCES users(id),
    PRIMARY KEY (software_name, version),
    CHECK (length(version) <= 100),
    CHECK ((retired_at IS NULL) = (retired_by IS NULL))
);

CREATE TABLE images (                               -- a container this deployment may run
    id            text PRIMARY KEY,
    registry_ref  text NOT NULL,                    -- what a human typed. Display and
                                                    -- re-resolution only
    digest        text NOT NULL UNIQUE,             -- 'sha256:<hex>' -- WHAT ACTUALLY RUNS
    resolved_at   text NOT NULL,                    -- when the tag was pinned to this digest
    built_at      text,                             -- when the IMAGE was built, from its own
                                                    -- manifest. NULL = the manifest said nothing.
                                                    -- Ranks before resolved_at, the pin time,
                                                    -- or an old image registered today would be
                                                    -- newest. Breaks the tie between images of
                                                    -- IDENTICAL versions; where equal or NULL
                                                    -- (ko, Nix and Bazel stamp 1970 by design),
                                                    -- the later resolved_at does
    registered_by text REFERENCES users(id),        -- a person, in the portal...
    registered_via text,                            -- ...or 'derived': the server built it. CI
                                                    -- registration is crucible's
    derived_from  text REFERENCES images(id),       -- the image a node's Python layer was built
                                                    -- on. NULL for a registered image
    derivation    text,                             -- the cache key: a hash of the base digest,
                                                    -- the requirements and constraints the
                                                    -- server wrote, the wheels' digests and the
                                                    -- requested_versions.python names
    installed     text,                             -- JSON [[name, version]] the layer holds:
                                                    -- what `resolved_versions` adds for a node
                                                    -- in it. No image_contents of its own, so it
                                                    -- never satisfies a requirement nor is
                                                    -- advertised
    note          text,
    retired_at    text,
    retired_by    text REFERENCES users(id),
    CHECK (digest LIKE 'sha256:%'),
    CHECK ((retired_at IS NULL) = (retired_by IS NULL)),
    CHECK ((registered_by IS NULL) <> (registered_via IS NULL)),  -- exactly one
    CHECK ((derived_from IS NULL) = (derivation IS NULL)),
    CHECK ((derived_from IS NULL) = (registered_via IS NOT 'derived')),
    CHECK ((derived_from IS NULL) = (installed IS NULL)),
    UNIQUE (derived_from, derivation)
);

CREATE TABLE image_contents (                       -- what is INSIDE it -- declared, not derived,
    image_id      text NOT NULL                     -- so a wrong row fails at run time rather
                    REFERENCES images(id) ON DELETE CASCADE,   -- than at submit
    software_name text NOT NULL,
    version       text NOT NULL,
    PRIMARY KEY (image_id, software_name, version),
    FOREIGN KEY (software_name, version)
        REFERENCES software_versions (software_name, version)
);
CREATE INDEX image_contents_lookup_idx ON image_contents (software_name, version);


-- SPARSE: a row exists only where somebody overrode something, and a NULL
-- column inherits the deployment's value from config.json. The contract pairs
-- this table with `plans`, which this profile does not have: hence no `plan_id`.
--
-- The encoding is three-valued and it is the contract's:
--   NULL  inherit
--   -1    UNLIMITED
--   >= 0  that value
-- `-1` never reaches a client, where `null` means *unlimited*. A CHECK on every
-- column, so a typo cannot make a negative limit two paths read differently.
--
-- Written by the OPERATOR CLI, never the portal: a ceiling is policy and
-- this deployment has no admin mode. The account screen renders it read-only.
CREATE TABLE user_limits (                          -- sparse: only the overrides
    user_id             text PRIMARY KEY REFERENCES users(id),
    max_download_bytes  integer                     -- NULL inherits, -1 is unlimited
        CHECK (max_download_bytes IS NULL OR max_download_bytes >= -1),
    set_at              text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    set_by              text NOT NULL REFERENCES users(id),
    note                text                        -- why, for the person who reads it later
);
