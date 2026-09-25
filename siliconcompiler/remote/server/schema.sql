-- The v1 store: 18 tables of the contract's 41.
--
-- The shape of every table here is the contract's. What differs is the engine
-- and the subset: sc-server is the unauthenticated profile plus the image
-- registry, so entitlements, terms, projects, the artifact gate, the admin
-- tables and metering are absent. A dropped table takes its foreign keys with
-- it, and every such removal is commented where it happens.
--
-- Translating Postgres to SQLite, once, here:
--
--   uuid          -> text, the canonical hyphenated form of a UUIDv7
--   timestamptz   -> text, RFC 3339 in UTC ('2026-09-22T11:22:33.456Z')
--   jsonb         -> text holding JSON; the JSON1 functions read it in place
--   boolean       -> integer constrained to 0 or 1
--   bigserial     -> integer primary key, which SQLite aliases to the rowid
--   inet, char(32)-> text
--   now()         -> strftime, so a default and a Python write agree on format
--
-- `index` is a SQLite keyword, so the node column of that name is quoted
-- everywhere it appears. Foreign keys are declared but only enforced when the
-- connection sets `PRAGMA foreign_keys = ON`, which store.py does.

PRAGMA foreign_keys = ON;


--------------------------------------------------------------------------
-- 1. Identity
--------------------------------------------------------------------------

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
                                                    -- everyone is an admin on this deployment, so
                                                    -- nothing reads this. It stays for one shape
                                                    -- with crucible
    is_active       integer NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at      text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_seen_at    text,
    deactivated_at  text,
    UNIQUE (issuer, subject)
);
CREATE UNIQUE INDEX users_email_key ON users (lower(email)) WHERE email IS NOT NULL;


--------------------------------------------------------------------------
-- 2. Sessions and devices
--------------------------------------------------------------------------

CREATE TABLE devices (
    id                 text PRIMARY KEY,
    user_id            text NOT NULL REFERENCES users(id),
    name               text NOT NULL,               -- renamed in the portal; there is no
                                                    -- API endpoint for it
    dpop_jkt           text NOT NULL,               -- JWK thumbprint: THIS is the pin. Nothing
                                                    -- verifies the identity in this profile, so
                                                    -- the key binding a session to a machine is
                                                    -- the only real control the mode has
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
                                                    -- the vocabulary is the contract's and stays
                                                    -- closed. Only 'interactive' is ever written
                                                    -- here: minting a CI credential is crucible's
                                                    -- path, and ci_credentials is not in this
                                                    -- profile -- which is also why the
                                                    -- ci_credential_id column and its foreign key
                                                    -- are absent rather than left dangling
    dpop_jkt            text NOT NULL,              -- the key this family is bound to, checked on
                                                    -- every refresh. NOT NULL admits no exception
    scope               text NOT NULL,              -- the CEILING, space-delimited and ALREADY
                                                    -- EXPANDED: jobs:write is stored as
                                                    -- 'jobs:read jobs:write'. A rotation may
                                                    -- narrow inside it, never widen
    created_at          text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    absolute_expires_at text NOT NULL,              -- set at creation, NEVER extended by a
                                                    -- refresh or by activity
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
    expires_at   text NOT NULL,                     -- CLAMPED to the family's
                                                    -- absolute_expires_at; never past it
    revoked_at   text,
    replaced_by  text REFERENCES refresh_tokens(jti),
    replaced_at  text
);
CREATE INDEX refresh_family_idx ON refresh_tokens (family_id);


--------------------------------------------------------------------------
-- 4. Jobs
--------------------------------------------------------------------------

CREATE TABLE job_states (                           -- the closed set, as a table
    state    text PRIMARY KEY,
    terminal integer NOT NULL CHECK (terminal IN (0, 1))
);
INSERT INTO job_states VALUES
    ('created', 0), ('awaiting_input', 0), ('queued', 0), ('running', 0),
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
    ('preparing', 0),           -- dispatched, fetching its image: a tool image is minutes, and
                                -- without this the wait is indistinguishable from a hang
    ('running', 0),
    ('completed', 1), ('failed', 1),
    ('skipped', 1),             -- deliberately not run: a condition, a cached hit
    ('cancelled', 1);           -- the job ended before this node started

CREATE TABLE jobs (
    id                text PRIMARY KEY,             -- one opaque id, not the content hash
    user_id           text NOT NULL REFERENCES users(id),
                                                    -- project_id is absent: 'projects' is not in
                                                    -- this deployment's features
    device_id         text REFERENCES devices(id),  -- which machine submitted it

    state             text NOT NULL REFERENCES job_states(state),
    state_changed_at  text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                                                    -- PUBLISHED on the job object under this same
                                                    -- name, written on every transition

    design            text NOT NULL,
    jobname           text NOT NULL,
    manifest_flow     text,                         -- which flowgraph ran, re-derived at submit

    descriptor        text NOT NULL,                -- JSON: POST /v1/jobs exactly as asserted
    manifest_nodes    integer,                      -- re-derived at submit
    manifest_tools    text,                         -- JSON, re-derived at submit
    manifest_pdk      text,                         -- re-derived at submit: a PDK name, or the
                                                    -- literal 'none' = this flow requires no PDK

    upload_key              text,                   -- the object key the grant was issued for
    upload_location_id      text REFERENCES storage_locations(id),
    upload_digest           text,                   -- 'sha256:<hex>', asserted at submit and
                                                    -- verified against what storage reports
    upload_bytes            integer,
    upload_grant_expires_at text,                   -- also the reaper's trigger
    upload_revoked_at       text,

    idempotency_key        text,
    submit_idempotency_key text,
    run_hash          text,                         -- the client's opaque hash of the work, for
                                                    -- job reuse. The server never recomputes or
                                                    -- normalises it, and the lookup is
                                                    -- owner-scoped, which is what makes trusting
                                                    -- a client-supplied value safe: a wrong hash
                                                    -- hands a user their own stale job
    job_identity      text,                         -- H(run_hash || the digests this job's
                                                    -- declared versions resolved to). What reuse
                                                    -- is actually keyed on: the client keeps
                                                    -- computing its own hash and tracks nothing
                                                    -- extra, and the server folds in what IT
                                                    -- chose -- so re-registering an image
                                                    -- invalidates reuse exactly when it should,
                                                    -- because a new digest is precisely
                                                    -- "the code changed"
    image_id          text REFERENCES images(id),   -- the container this job RAN IN, resolved at
                                                    -- submit. NULL before admission, and on a
                                                    -- deployment that runs no containers
    scheduler_job_id  text,                         -- set only where the JOB is the unit of
                                                    -- submission; per-node dispatch puts it on
                                                    -- job_nodes instead. At most one level
    submit_trace_id   text CHECK (submit_trace_id IS NULL OR length(submit_trace_id) = 32),
    error_type        text,                         -- the RFC 9457 `type` URI

    created_at        text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    submitted_at      text,
    started_at        text,
    finished_at       text,
    cancel_requested_at text,
    retention_until   text,
    archived_at       text,                         -- VIEW ONLY: the job leaves the default list
                                                    -- and is unchanged in every other respect
    archived_by       text REFERENCES users(id),
    deleted_at        text,                         -- the job stays readable after DELETE;
                                                    -- subresources 404. A `deleted` state was
                                                    -- refused because it would erase whether the
                                                    -- job had completed, failed or been rejected
    deleted_by        text REFERENCES users(id),

    -- A job that was admitted has a resolved PDK. 'cancelling' joins the named
    -- side because it is post-admission.
    CONSTRAINT jobs_admitted_pdk_resolved
        CHECK (state NOT IN ('queued', 'running', 'cancelling', 'completed', 'failed')
               OR (manifest_pdk IS NOT NULL AND manifest_pdk <> '')),
    -- Only a job that has stopped may be archived. The terminal five are spelled
    -- out because a CHECK cannot read job_states.terminal.
    CONSTRAINT jobs_archived_is_terminal
        CHECK (archived_at IS NULL
               OR state IN ('completed', 'failed', 'cancelled', 'rejected', 'abandoned')),
    CHECK ((archived_at IS NULL) = (archived_by IS NULL)),
    CHECK ((deleted_at IS NULL) = (deleted_by IS NULL))
);
CREATE UNIQUE INDEX jobs_idempotency_idx ON jobs (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX jobs_submit_idempotency_idx ON jobs (user_id, submit_idempotency_key)
    WHERE submit_idempotency_key IS NOT NULL;
-- This index IS the published collection ordering. GET /v1/jobs is ordered
-- created_at DESC with the opaque id as a bytewise tiebreaker, and ?cursor= is a
-- keyset over exactly that pair. The partial predicate is why a deleted job
-- leaves the list.
CREATE INDEX jobs_list_idx ON jobs (user_id, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NULL;
-- ?archived=true is the SAME ordering over the complement, so a client pages
-- both views identically. Two partial indexes rather than one wider one: the
-- default list is the hot path and must not carry the archive's rows.
CREATE INDEX jobs_archived_idx ON jobs (user_id, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NOT NULL;
CREATE INDEX jobs_design_idx ON jobs (user_id, design, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NULL;
CREATE INDEX jobs_jobname_idx ON jobs (user_id, jobname, created_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NULL;
CREATE INDEX jobs_active_idx ON jobs (user_id)
    WHERE state IN ('queued', 'running', 'cancelling');
CREATE INDEX jobs_pending_idx ON jobs (user_id) WHERE state IN ('created', 'awaiting_input');
-- Owner-scoped, per the reuse rule, and partial because almost no row has one.
-- On job_identity and not run_hash: two runs asking for the same work but
-- resolved to different images are correctly different jobs.
CREATE INDEX jobs_run_hash_idx ON jobs (user_id, job_identity)
    WHERE job_identity IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE job_state_transitions (                -- append-only
    id            integer PRIMARY KEY,
    job_id        text NOT NULL REFERENCES jobs(id),
    from_state    text REFERENCES job_states(state),
    to_state      text NOT NULL REFERENCES job_states(state),
    actor_user_id text REFERENCES users(id),        -- the person who caused it, where a person
                                                    -- did. NULL = the scheduler, the worker or
                                                    -- the reaper
                                                    -- elevation_id is absent: there is no
                                                    -- administrative mode here to record
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


--------------------------------------------------------------------------
-- 5. Artifacts
--------------------------------------------------------------------------

CREATE TABLE artifact_kinds (                       -- the vocabulary, and how long each kind is
    kind           text PRIMARY KEY,                -- kept. retention_days is a floor that is READ
    retention_days integer
                     CHECK (retention_days IS NULL OR retention_days > 0)
);
INSERT INTO artifact_kinds (kind, retention_days) VALUES
    ('manifest', 1825),      -- what the run WAS: small, and the thing you want years later
    ('logs',     1825),
    ('reports',  1825),
    ('issue',    1825),      -- a failure is what you come back to
    ('final',    1825),      -- the deliverables. Re-making one is a re-run
    ('outputs',  NULL),      -- large, regenerable, and the most sensitive: the floor, no more
    ('input',    NULL),      -- the uploaded archive. The owner has a copy
    ('node',     NULL);      -- one node's whole working directory, and it may never outlive
                             -- its contents. ALWAYS bound to a step and an index: there is no
                             -- job-level tarball, because the kind is named for what it is
-- Starting values. The numbers are the deployment's; the SHAPE is the contract.
-- The set is CLOSED and PUBLISHED, so a new value is a version bump.

CREATE TABLE storage_locations (                    -- WHERE 'where' is
    id       text PRIMARY KEY,                      -- 'primary', 'archive-2026'
    uri_base text NOT NULL,                         -- 'file:///srv/artifacts/' -- read to build a
                                                    -- URL. A URI, so file:// is a first-class
                                                    -- deployment and needs no second shape
    writable integer NOT NULL DEFAULT 1 CHECK (writable IN (0, 1))
                                                    -- false after a migration: still read, never
                                                    -- written to again. SEVERAL may be writable
);

CREATE TABLE artifacts (
    id            text PRIMARY KEY,
    job_id        text NOT NULL REFERENCES jobs(id),
    step          text,                             -- 'place'; NULL for job-level artifacts
    "index"       text,                             -- '0'; NULL for job-level artifacts
    content_hash  text NOT NULL,                    -- WHAT the bytes are: 'sha256:<hex>'.
                                                    -- Integrity, and the dedup identity
    location_id   text NOT NULL REFERENCES storage_locations(id),
    storage_key   text NOT NULL,                    -- WHERE in it. Never on the wire, and MAY be
                                                    -- shared between rows
    size_bytes    integer NOT NULL,
    media_type    text,
    kind          text NOT NULL REFERENCES artifact_kinds(kind),
    created_at    text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    retention_until text,
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
    delete_reason text,                             -- person deleted it on purpose, and owes a
                                                    -- reason
    CHECK (("index" IS NULL) = (step IS NULL)),     -- both, or neither. Deliberately NOT a
                                                    -- foreign key into job_nodes
    CHECK (legal_hold_at IS NULL
        OR (legal_hold_by IS NOT NULL AND legal_hold_reason IS NOT NULL)),
    CHECK ((withheld_at IS NULL) = (withheld_by IS NULL)),
    CHECK (NOT (legal_hold_at IS NOT NULL AND deleted_at IS NOT NULL)),
    CHECK (deleted_at IS NOT NULL OR (deleted_by IS NULL AND delete_reason IS NULL)),
    CHECK (deleted_by IS NULL OR delete_reason IS NOT NULL)
);
CREATE INDEX artifacts_live_hash_idx ON artifacts (content_hash) WHERE deleted_at IS NULL;
CREATE INDEX artifacts_job_idx ON artifacts (job_id);
CREATE INDEX artifacts_node_idx ON artifacts (job_id, step, "index");
CREATE INDEX artifacts_hash_idx ON artifacts (content_hash);

-- 🔴 One row per kind per node, and it has to be the DATABASE that says so.
-- Indexing is driven from reconcile, which runs on whichever request thread
-- got there first -- and a client polling its job while tailing two logs has
-- three of them. Every writer checks before inserting, and two that check
-- together both pass: the aes flow came back with 38 bundles for 23 nodes, and
-- the portal showed a node owning "logs, bundle, bundle".
--
-- coalesce because the job-level rows carry NULL for both, and SQLite counts
-- NULLs as distinct in a unique index -- which would leave exactly the rows
-- with no node unprotected.
CREATE UNIQUE INDEX artifacts_one_per_node_idx
    ON artifacts (job_id, kind, coalesce(step, ''), coalesce("index", ''));


--------------------------------------------------------------------------
-- 8. Software and images
--------------------------------------------------------------------------

CREATE TABLE software (                             -- what this deployment knows how to run
    name          text PRIMARY KEY,                 -- the DISTRIBUTION name, and the wire key:
                                                    -- 'siliconcompiler', 'openroad'
    display_name  text NOT NULL,
    kind          text NOT NULL                     -- which bucket it is published in, and which
                    CHECK (kind IN                  -- question the resolution asks about it
                      ('python',                    -- a distribution in the interpreter. The whole
                                                    -- python set has to be satisfied by ONE image,
                                                    -- because they share a process
                       'tool')),                    -- an executable. Satisfied PER NODE, by an
                                                    -- image holding the python set and this tool
                                                    -- 🔴 Derived and never typed: the mechanism
                                                    -- that reads the version IS the
                                                    -- classification. importlib.metadata answers
                                                    -- for a python distribution and exe+vswitch
                                                    -- for a tool, so there is no third question
                                                    -- and no field to get wrong. See probe.py
    driver        text,                             -- the module carrying this tool's Task driver:
                                                    -- 'siliconcompiler.tools.openroad'. NULL for a
                                                    -- python distribution, and for a tool nobody
                                                    -- here drives.
                                                    -- 🔴 RECORDED and not re-derived. A driver can
                                                    -- live in any package -- a site library ships
                                                    -- its own and a proprietary tool's never will
                                                    -- be in this tree -- and the in-tree path is
                                                    -- not even reliable in-tree: 'kepler-formal'
                                                    -- is driven from ...tools.keplerformal. It is
                                                    -- filled in by scanning at registration, so
                                                    -- nothing has to be typed for a driver this
                                                    -- process can already see
    version_package text,                           -- read this tool's version from a PYTHON
                                                    -- distribution of this name instead of by
                                                    -- running it: 'pyslang' for the tool 'slang'.
                                                    -- 🔴 A tool can have no executable at all --
                                                    -- slang's driver runs pyslang in the
                                                    -- framework's own process -- and still has to
                                                    -- be placed in an image holding it. The
                                                    -- distribution is NOT called what the tool is
                                                    -- called, which is why this is recorded and
                                                    -- not derived from the name
    added_at      text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    added_by      text NOT NULL REFERENCES users(id),
    retired_at    text,
    retired_by    text REFERENCES users(id),
    CHECK (length(name) <= 100),
    -- A python distribution has no task driver, because a task driver is what
    -- makes something a tool. The reverse is allowed: a tool this deployment
    -- lists and nobody here drives has no version to report, which is what
    -- `published_date` is for.
    CHECK (driver IS NULL OR kind = 'tool'),
    -- Same class of fact as `driver`: how do I get this name's version. A
    -- python distribution needs none -- its own name IS the answer -- so
    -- setting it there would be a second source for something already known.
    CHECK (version_package IS NULL OR kind = 'tool'),
    CHECK ((retired_at IS NULL) = (retired_by IS NULL))
);

CREATE TABLE software_versions (                    -- which versions of it, and in what order
    software_name text NOT NULL REFERENCES software(name),
    version       text NOT NULL,                    -- exact, and normalised to PEP 440 when the
                                                    -- image is registered. STORAGE has no ranges:
                                                    -- the wire carries specifiers and this is
                                                    -- what they are matched against
    version_source text NOT NULL DEFAULT 'reported' -- where the number came from
                     CHECK (version_source IN
                       ('reported',                 -- the tool said so. The ONLY kind that can
                                                    -- satisfy a version requirement
                        'published_date')),         -- it said nothing, so this is when the image
                                                    -- was published. A complete tool list beats a
                                                    -- partial one, but 20260924 beats 2.0.1 under
                                                    -- every comparison there is -- so it is
                                                    -- marked, it never satisfies a requirement,
                                                    -- and it always sorts BELOW a reported one
                                                    -- whatever the numbers say
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
                                                    -- 🔴 Never resolved_at: that records when the
                                                    -- operator pinned the tag, so registering a
                                                    -- two-year-old image today would make it the
                                                    -- newest -- and pinning an old image on
                                                    -- purpose is a reproducibility case, not a
                                                    -- mistake. Breaks the tie between two images
                                                    -- carrying IDENTICAL versions, which
                                                    -- preference cannot
    registered_by text REFERENCES users(id),        -- a person, in the portal. Always set here:
    registered_via text,                            -- the CI registration path is crucible's, so
                                                    -- every image on this deployment has a person
                                                    -- on it
    note          text,
    retired_at    text,
    retired_by    text REFERENCES users(id),
    CHECK (digest LIKE 'sha256:%'),
    CHECK ((retired_at IS NULL) = (retired_by IS NULL)),
    CHECK ((registered_by IS NULL) <> (registered_via IS NULL))   -- exactly one
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


--------------------------------------------------------------------------
-- 9. Per-user ceilings
--------------------------------------------------------------------------
-- 🔴 SPARSE: a row exists only where somebody overrode something, and a NULL
-- column inherits the deployment's value from config.json. The contract pairs
-- this table with `plans`, which this profile does not have -- there are no
-- named tiers here, so the thing inherited from is the operator's config
-- rather than a plan row. That is the one difference, and it is why
-- `plan_id` is absent.
--
-- 🔴 The encoding is three-valued and it is the contract's:
--   NULL  inherit
--   -1    UNLIMITED
--   >= 0  that value
-- `-1` never reaches a client -- the resolver turns it into the wire's `null`,
-- because the wire had already spent `null` on *unlimited* while this table
-- needed it for *inherit*. A CHECK on every column, because a sentinel with no
-- constraint is a typo away from a negative limit that reads as unlimited to
-- one path and refuse-everything to another.
--
-- ⚠️ Written by the OPERATOR and never by the portal. A ceiling is policy, and
-- this deployment has no admin mode: the only writer is the operator CLI, the
-- same way an image is registered. The account screen renders it read-only.
CREATE TABLE user_limits (                          -- sparse: only the overrides
    user_id             text PRIMARY KEY REFERENCES users(id),
    max_download_bytes  integer                     -- NULL inherits, -1 is unlimited
        CHECK (max_download_bytes IS NULL OR max_download_bytes >= -1),
    set_at              text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    set_by              text NOT NULL REFERENCES users(id),
    note                text                        -- why, for the person who reads it later
);
