'''
The v1 job store.

sc-server owns the schema that crucible implements, so the table shapes in
``schema.sql`` are the deliverable rather than a step toward one. The engine is
free to differ -- two implementations of one contract are supposed to -- and
SQLite is this one's: it is a file, it needs no service, and it is what makes
the compose rig sufficient on its own.
'''

import sqlite3
import threading

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from siliconcompiler.remote.server.ids import uuid7

__all__ = ["Store", "STORE_VERSION", "now"]


# Bumped whenever schema.sql changes shape. A store written by a newer server is
# refused rather than opened: an unrecognised column is a silent wrong answer,
# where a refusal is a message.
#
# Deliberately not `schemaversion`, which is SiliconCompiler's build schema and
# moves for unrelated reasons. This is the third independent version in the
# tree, alongside the package version, and it is the one a store file records.
STORE_VERSION = 2

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# RFC 3339 in UTC, to milliseconds -- the same spelling schema.sql's DEFAULTs
# produce, so a row written by Python and one written by the database sort and
# compare against each other.
_TIMESTAMP = "%Y-%m-%dT%H:%M:%S.%fZ"


def now() -> str:
    '''The current time, in the one format this store writes.'''
    # %f is microseconds and the column holds milliseconds; the slice is what
    # keeps a Python write byte-comparable with a DEFAULT.
    return datetime.now(timezone.utc).strftime(_TIMESTAMP)[:-4] + "Z"


class StoreVersionError(RuntimeError):
    '''The store on disk was written by a different version of this schema.'''


class Store:
    '''A connection to one deployment's store.

    Opening creates the file and the schema if they are not there, so a bare
    ``-datadir`` that has never been used starts a working server. Rows are
    returned as :class:`sqlite3.Row`, which reads like a mapping and keeps
    call sites from depending on column order.
    '''

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        fresh = not self.path.exists()

        # A sqlite3 connection belongs to the thread that opened it, and the
        # server answers each request on a worker thread, so one shared
        # connection would fail on every request that is not the first. Each
        # thread gets its own, opened on demand against the same file; WAL is
        # what lets those readers and the one writer proceed at the same time.
        self._local = threading.local()
        self._connections = []
        self._lock = threading.Lock()

        if fresh:
            self._create()
        self._check_version()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.path), isolation_level=None)
        con.row_factory = sqlite3.Row

        # Both of these are per connection rather than per database, so they
        # have to be set on every one. Foreign keys especially: missing it here
        # would leave the schema's references unenforced on worker threads and
        # enforced on the thread that happened to open the store, which is a
        # difference nothing would notice until a bad row was already written.
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 5000")
        # Set once on the file rather than per connection, but harmless to
        # repeat and cheaper than tracking whether it has been done.
        con.execute("PRAGMA journal_mode = WAL")

        with self._lock:
            self._connections.append(con)
        return con

    def _create(self) -> None:
        con = self.connection
        con.executescript(_SCHEMA_PATH.read_text())
        con.execute(f"PRAGMA user_version = {STORE_VERSION}")

    def _check_version(self) -> None:
        found = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if found != STORE_VERSION:
            raise StoreVersionError(
                f"{self.path} holds schema version {found}, and this server "
                f"speaks version {STORE_VERSION}")

    @property
    def connection(self) -> sqlite3.Connection:
        '''This thread's connection, opened the first time it asks.'''
        con = getattr(self._local, "con", None)
        if con is None:
            con = self._local.con = self._connect()
        return con

    def close(self) -> None:
        '''Close every connection this store handed out.

        Called from one thread while others may hold connections, which is safe
        here because closing happens at shutdown and on a store nobody is
        serving from.
        '''
        with self._lock:
            connections, self._connections = self._connections, []
        for con in connections:
            try:
                con.close()
            except sqlite3.Error:
                pass
        self._local = threading.local()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    ######################################################################
    # Queries
    ######################################################################

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        '''Run one parameterised statement.

        Every query in this server goes through here or its siblings with
        placeholders. Nothing interpolates a value into SQL: the job store holds
        user-supplied design names, job names and hashes, and an identity this
        deployment does not verify.
        '''
        return self.connection.execute(sql, params)

    def one(self, sql: str, params=()) -> Optional[sqlite3.Row]:
        '''The first row, or None.'''
        return self.connection.execute(sql, params).fetchone()

    def all(self, sql: str, params=()):
        '''Every row.'''
        return self.connection.execute(sql, params).fetchall()

    def transaction(self):
        '''A transaction context manager.

        ``isolation_level=None`` means the driver opens none of its own, so
        this is the only place a multi-statement write becomes atomic.
        '''
        return _Transaction(self.connection)

    ######################################################################
    # Writes every phase needs
    ######################################################################

    def upsert_user(self, issuer: str, subject: str, **fields) -> sqlite3.Row:
        '''Find the user for an (issuer, subject), creating it if new.

        Identity here is self-asserted namespacing rather than a boundary --
        anyone who can present the same derivation is the same principal
        already. What it buys is the thing that was actually broken: a job has
        an owner, and a stranger holding its id is not that owner.
        '''
        found = self.one(
            "SELECT * FROM users WHERE issuer = ? AND subject = ?", (issuer, subject))
        if found is not None:
            return found

        columns = ["id", "issuer", "subject"] + list(fields)
        values = [str(uuid7()), issuer, subject] + list(fields.values())
        self.execute(
            f"INSERT INTO users ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' * len(columns))})",
            values)
        return self.one(
            "SELECT * FROM users WHERE issuer = ? AND subject = ?", (issuer, subject))

    def ensure_storage_location(self, location_id: str, uri_base: str) -> None:
        '''Declare where this deployment keeps bytes.

        The location is a row and ``uri_base`` is a URI, so ``file://`` needs no
        second shape -- this is the deployment that argument was made for.
        '''
        self.execute(
            "INSERT INTO storage_locations (id, uri_base, writable) VALUES (?, ?, 1) "
            "ON CONFLICT (id) DO UPDATE SET uri_base = excluded.uri_base",
            (location_id, uri_base))

    ######################################################################
    # Reads the capabilities block needs
    ######################################################################

    def advertised_software(self, containers: bool = True) -> dict:
        '''``GET /v1``'s ``software`` map: every runnable version, best first.

        🔴 **On a deployment that runs containers a version is advertised only
        where a live image holds it**, so this is a join and not a listing.
        Without that filter the trap is the familiar one: a version registered
        and never put in an image is advertised as supported and refused at
        submit, and the client did exactly what it was told.

        ⚠️ **Where nothing runs in a container the join would be a lie in the
        other direction.** Such a deployment has no images by definition, so
        joining to them would advertise nothing at all while the versions it
        genuinely runs sit in the table. It lists what it tracks.
        '''
        joins = (
            "JOIN image_contents ic "
            "  ON ic.software_name = sv.software_name AND ic.version = sv.version "
            "JOIN images i ON i.id = ic.image_id AND i.retired_at IS NULL "
        ) if containers else ""

        rows = self.all(
            "SELECT DISTINCT sv.software_name AS name, sv.version, sv.preference "
            "FROM software_versions sv "
            "JOIN software s ON s.name = sv.software_name "
            f"{joins}"
            "WHERE s.retired_at IS NULL "
            "  AND sv.retired_at IS NULL "
            "ORDER BY sv.software_name, sv.preference DESC, sv.version DESC")

        software: dict = {}
        for row in rows:
            software.setdefault(row["name"], []).append(row["version"])
        return software


class _Transaction:
    def __init__(self, con: sqlite3.Connection):
        self._con = con

    def __enter__(self) -> sqlite3.Connection:
        self._con.execute("BEGIN")
        return self._con

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self._con.execute("COMMIT")
        else:
            self._con.execute("ROLLBACK")
        return False
