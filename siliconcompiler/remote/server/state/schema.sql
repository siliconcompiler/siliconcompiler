-- The server's store. Timestamps are epoch seconds.

CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    issuer       TEXT NOT NULL,
    subject      TEXT NOT NULL,
    display_name TEXT,
    created_at   REAL NOT NULL,
    UNIQUE (issuer, subject)
);

-- The live row of a user is the key its subject is bound to; revoking it frees
-- the subject for the next key.
CREATE TABLE IF NOT EXISTS devices (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users (id),
    name              TEXT NOT NULL,
    jkt               TEXT NOT NULL,
    machine_id_source TEXT NOT NULL,
    enrolled_at       REAL NOT NULL,
    last_seen_at      REAL NOT NULL,
    revoked_at        REAL
);

-- Access and refresh tokens, by the hash of the opaque value. A session is the
-- tokens sharing a `session_id`; its end is `revoked_at` on all of them.
CREATE TABLE IF NOT EXISTS tokens (
    hash               TEXT PRIMARY KEY,
    kind               TEXT NOT NULL CHECK (kind IN ('access', 'refresh')),
    session_id         TEXT NOT NULL,
    user_id            TEXT NOT NULL REFERENCES users (id),
    device_id          TEXT NOT NULL REFERENCES devices (id),
    jkt                TEXT NOT NULL,
    expires_at         REAL NOT NULL,
    session_expires_at REAL NOT NULL,
    revoked_at         REAL
);
CREATE INDEX IF NOT EXISTS tokens_by_session ON tokens (session_id);
CREATE INDEX IF NOT EXISTS tokens_by_device ON tokens (device_id);

-- `upload_size` and `upload_digest` are what the first grant bound; the digest is
-- checked against the file on disk at submit.
CREATE TABLE IF NOT EXISTS jobs (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users (id),
    design           TEXT NOT NULL,
    jobname          TEXT NOT NULL,
    state            TEXT NOT NULL,
    flow             TEXT,
    idempotency_key  TEXT,
    upload_size      INTEGER,
    upload_digest    TEXT,
    scheduler_job_id TEXT,
    error            TEXT,
    created_at       REAL NOT NULL,
    submitted_at     REAL,
    started_at       REAL,
    finished_at      REAL,
    deleted_at       REAL,
    collected_at     REAL,
    UNIQUE (user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS jobs_by_user ON jobs (user_id, created_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS job_transitions (
    job_id TEXT NOT NULL REFERENCES jobs (id),
    state  TEXT NOT NULL,
    at     REAL NOT NULL,
    reason TEXT
);
CREATE INDEX IF NOT EXISTS transitions_by_job ON job_transitions (job_id);

CREATE TABLE IF NOT EXISTS job_nodes (
    job_id      TEXT NOT NULL REFERENCES jobs (id),
    step        TEXT NOT NULL,
    idx         TEXT NOT NULL,
    state       TEXT NOT NULL,
    started_at  REAL,
    finished_at REAL,
    exit_code   INTEGER,
    PRIMARY KEY (job_id, step, idx)
);

-- Each is a gzip file under ``artifacts/<job_id>/<id>``, made once from the run's tree.
CREATE TABLE IF NOT EXISTS artifacts (
    id         TEXT PRIMARY KEY,
    job_id     TEXT NOT NULL REFERENCES jobs (id),
    kind       TEXT NOT NULL,
    step       TEXT,
    idx        TEXT,
    size_bytes INTEGER NOT NULL,
    digest     TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS artifacts_by_job ON artifacts (job_id);
