'''
The v1 job store.

``schema.sql``'s table shapes are the v1 schema's, and the deliverable. The
engine may differ; SQLite is this one's because it is a file and needs no
service.
'''

import sqlite3
import threading
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple, Union


__all__ = ["Store", "STORE_VERSION", "now", "stamp", "parse", "TERMINAL_STATES",
           "TERMINAL_NODE_STATES", "PENDING_STATES", "ACTIVE_STATES"]


# Bumped whenever schema.sql changes shape, or the JSON a column holds does; a
# store at another version is refused. Not `schemaversion`, which is
# SiliconCompiler's build schema.
STORE_VERSION = 21

# Tries at an admission's lock, each waiting the busy timeout, before
# contention is this server's failure.
ADMISSION_ATTEMPTS = 5

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# The closed sets schema.sql's `job_states` and `node_states` hold.
# A job's terminal five, published as `terminal` on the job object.
TERMINAL_STATES = frozenset(
    ("completed", "failed", "cancelled", "rejected", "abandoned"))
TERMINAL_NODE_STATES = frozenset(("completed", "failed", "skipped", "cancelled"))
# Waiting for its upload: what `pending_uploads` counts.
PENDING_STATES = ("created", "awaiting_input")
# Work in flight, `staging` included: what `concurrent_jobs` counts.
ACTIVE_STATES = ("staging", "queued", "running", "cancelling")


def stamp(moment: datetime) -> str:
    '''A UTC ``moment`` in this store's one format, RFC 3339 to milliseconds:
    what schema.sql's DEFAULTs write, so all rows compare as strings.'''
    # %f is microseconds; the slice keeps a Python write comparable to a DEFAULT.
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse(text: str) -> datetime:
    '''The UTC moment a timestamp in this store's format names: `stamp`'s
    inverse. ValueError where ``text`` is not one.'''
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def now() -> str:
    '''The current time, in the one format this store writes.'''
    return stamp(datetime.now(timezone.utc))


class StoreVersionError(RuntimeError):
    '''The store on disk was written by a different version of this schema.'''


class Store:
    '''A connection to one deployment's store, creating the file and schema
    if they are not there. Rows are :class:`sqlite3.Row`.'''

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        fresh = not self.path.exists()

        # A sqlite3 connection belongs to its thread, so each thread opens its
        # own; WAL lets those readers and the one writer proceed together.
        # And each is closed when its thread is done: the server starts a
        # thread per request, and connections kept for the process's life
        # (three descriptors each under WAL) exhaust descriptors in minutes.
        # See `release` and `_reap`.
        self._local = threading.local()
        self._connections: List[Tuple[threading.Thread, sqlite3.Connection]] = []
        self._lock = threading.Lock()

        if fresh:
            self._create()
        self._check_version()

    def _connect(self) -> sqlite3.Connection:
        # So `_reap` and `close` can close it from another thread; it is still
        # only USED by the thread that opened it.
        con = sqlite3.connect(str(self.path), isolation_level=None,
                              check_same_thread=False)
        con.row_factory = sqlite3.Row

        # Per connection, so set on every one: without it the schema's foreign
        # keys would go unenforced on worker threads.
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 5000")
        # Per file, but harmless to repeat.
        con.execute("PRAGMA journal_mode = WAL")

        with self._lock:
            self._reap()
            self._connections.append((threading.current_thread(), con))
        return con

    def _reap(self) -> None:
        '''Close the connections of threads that have ended; the caller holds
        the lock. The backstop for `release`, so connections held are bounded
        by threads alive, not requests served.'''
        alive = []
        for thread, con in self._connections:
            if thread.is_alive():
                alive.append((thread, con))
            else:
                _close(con)
        self._connections = alive

    def release(self) -> None:
        '''Close THIS thread's connection, if it has one. Called as a request
        ends, and by a log stream, whose generator outlives its request.'''
        con = getattr(self._local, "con", None)
        if con is None:
            return
        self._local.con = None
        with self._lock:
            self._connections = [(thread, held) for thread, held in self._connections
                                 if held is not con]
        _close(con)

    def _create(self) -> None:
        con = self.connection
        con.executescript(_SCHEMA_PATH.read_text())
        con.execute(f"PRAGMA user_version = {STORE_VERSION}")

    def _check_version(self) -> None:
        '''Refuse a store this server does not speak, and say what to do.

        No migration, deliberately: this is a demo, test rig and reference
        implementation. The refusal names a next step instead.
        '''
        found = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if found == STORE_VERSION:
            return

        if found > STORE_VERSION:
            advice = ("Upgrade this server: the store was written by a newer "
                      "one, and opening it here would read columns this build "
                      "does not know about.")
        else:
            advice = (f"There is no migration. Move {self.path} aside and let "
                      "this server create a new one -- the jobs it holds stay "
                      "readable with the older server that wrote them, and "
                      "nothing on disk is deleted by doing so.")

        raise StoreVersionError(
            f"{self.path} holds schema version {found}, and this server "
            f"speaks version {STORE_VERSION}. {advice}")

    @property
    def connection(self) -> sqlite3.Connection:
        '''This thread's connection, opened the first time it asks.'''
        con = getattr(self._local, "con", None)
        if con is None:
            con = self._local.con = self._connect()
        return con

    def close(self) -> None:
        '''Close every connection this store handed out: only at shutdown, or on
        a store nobody is serving from.'''
        with self._lock:
            connections, self._connections = self._connections, []
        for _, con in connections:
            _close(con)
        self._local = threading.local()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        '''Run one parameterised statement. Nothing interpolates a value into
        SQL: names, hashes and identities here are user-supplied.'''
        return self.connection.execute(sql, params)

    def one(self, sql: str, params=()) -> Optional[sqlite3.Row]:
        '''The first row, or None.'''
        return self.connection.execute(sql, params).fetchone()

    def all(self, sql: str, params=()):
        '''Every row.'''
        return self.connection.execute(sql, params).fetchall()

    def transaction(self):
        '''A transaction context manager: with ``isolation_level=None`` this is
        the only place a multi-statement write becomes atomic.'''
        return _Transaction(self.connection)

    def admission(self, work: Callable[[], Any], attempts: int = ADMISSION_ATTEMPTS) -> Any:
        '''Run ``work`` -- a count and the write it decides -- as one
        transaction no other admission can interleave with; return its result.

        A numeric `pending_uploads` or `concurrent_jobs` is a hard ceiling.
        ``BEGIN IMMEDIATE`` takes SQLite's write lock BEFORE the count, so two
        admissions cannot both read one count and both insert, as a deferred
        ``BEGIN`` allows.

        Only the ``BEGIN IMMEDIATE`` waits on the lock, which it holds to the
        commit, so only it is retried, never one statement alone; ``work`` runs
        once, since it may move a file. A `ProblemError` from it rolls back.
        '''
        import time

        con = self.connection
        for attempt in range(attempts):
            try:
                con.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError as e:
                text = str(e).lower()
                if not ("locked" in text or "busy" in text) or attempt == attempts - 1:
                    raise
                time.sleep(0.05 * 2 ** attempt)
        try:
            result = work()
        except BaseException:
            con.execute("ROLLBACK")
            raise
        con.execute("COMMIT")
        return result

    def upsert_user(self, issuer: str, subject: str, **fields) -> sqlite3.Row:
        '''Find or create the user for an (issuer, subject): self-asserted
        namespacing, not a boundary (see `identity.auth`).'''
        found = self.one(
            "SELECT * FROM users WHERE issuer = ? AND subject = ?", (issuer, subject))
        if found is not None:
            return found

        columns = ["id", "issuer", "subject"] + list(fields)
        values = [str(uuid.uuid4()), issuer, subject] + list(fields.values())
        self.execute(
            f"INSERT INTO users ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' * len(columns))})",
            values)
        return self.one(
            "SELECT * FROM users WHERE issuer = ? AND subject = ?", (issuer, subject))

    def ensure_storage_location(self, location_id: str, uri_base: str) -> None:
        '''Declare where this deployment keeps bytes.'''
        self.execute(
            "INSERT INTO storage_locations (id, uri_base, writable) VALUES (?, ?, 1) "
            "ON CONFLICT (id) DO UPDATE SET uri_base = excluded.uri_base",
            (location_id, uri_base))

    def advertised_software(self, containers: bool = True) -> dict:
        '''``GET /v1``'s ``software``: every runnable version, best first, by
        bucket.

        `python`, `tools` and `interpreter` are a CLOSED set, every one always
        present and possibly `{}` (`images.BUCKETS`); they are separate because
        they are satisfied differently (`jobs.common.requirements`).

        With containers, a version is advertised only where a live image holds
        it, or one never put in an image is advertised and refused at submit.
        Without containers there are no images, so it lists what it tracks.

        The frozen flat shape has no room for `version_source`, so a dated
        version is advertised beside a reported one. Accepted because the
        preflight is advisory and the refusal says *present but reports no
        version*; checks that must tell them apart read `reported_versions`.
        '''
        return self._software(containers)

    def reported_versions(self, containers: bool = True) -> dict:
        '''The same map, less every version no tool reported.

        The set a version REQUIREMENT is matched against: a date such as
        `20260924` beats `2.0.1` under every PEP 440 comparison.
        '''
        return self._software(containers, reported_only=True)

    def _software(self, containers: bool, reported_only: bool = False) -> dict:
        joins = (
            "JOIN image_contents ic "
            "  ON ic.software_name = sv.software_name AND ic.version = sv.version "
            "JOIN images i ON i.id = ic.image_id AND i.retired_at IS NULL "
            "  AND i.derived_from IS NULL "
        ) if containers else ""

        reported = "  AND sv.version_source = 'reported' " if reported_only else ""

        rows = self.all(
            "SELECT DISTINCT sv.software_name AS name, sv.version, sv.preference, "
            "       sv.version_source, s.kind "
            "FROM software_versions sv "
            "JOIN software s ON s.name = sv.software_name "
            f"{joins}"
            "WHERE s.retired_at IS NULL "
            "  AND sv.retired_at IS NULL "
            f"{reported}"
            "ORDER BY sv.software_name, "
            # Reported first whatever the numbers say, or an old unversioned
            # build heads the list for ever.
            "         CASE sv.version_source WHEN 'reported' THEN 0 ELSE 1 END, "
            "         sv.preference DESC, sv.version DESC")

        from siliconcompiler.remote.server.software.images import BUCKETS

        software: dict = {bucket: {} for bucket in BUCKETS.values()}
        for row in rows:
            software[BUCKETS[row["kind"]]].setdefault(row["name"], []).append(
                row["version"])
        return software


class _Transaction:
    '''One transaction, holding the write lock from its first statement.

    `BEGIN IMMEDIATE`, never a deferred `BEGIN`: under WAL, a deferred read
    then write after another commit fails at once (`SQLITE_BUSY_SNAPSHOT`),
    which the busy timeout never waits out.
    '''

    def __init__(self, con: sqlite3.Connection):
        self._con = con

    def __enter__(self) -> sqlite3.Connection:
        self._con.execute("BEGIN IMMEDIATE")
        return self._con

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self._con.execute("COMMIT")
        else:
            self._con.execute("ROLLBACK")
        return False


def _close(con: sqlite3.Connection) -> None:
    try:
        con.close()
    except sqlite3.Error:
        pass
