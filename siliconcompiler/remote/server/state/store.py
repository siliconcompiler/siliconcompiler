'''The server's SQLite store: one file, one connection per thread.'''

import sqlite3
import threading

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

__all__ = ["Store", "iso"]


_SCHEMA = Path(__file__).with_name("schema.sql")


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    '''Rows are :class:`sqlite3.Row`. A connection belongs to its thread, and
    a thread that outlives its request calls :meth:`release` when done.'''

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.connection.executescript(_SCHEMA.read_text())

    @property
    def connection(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(self.path, isolation_level=None)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys = ON")
            con.execute("PRAGMA busy_timeout = 5000")
            # Readers proceed alongside the one writer.
            con.execute("PRAGMA journal_mode = WAL")
            self._local.con = con
        return con

    def release(self) -> None:
        '''Close this thread's connection: the server starts a thread per
        request, and open files add up.'''
        con = getattr(self._local, "con", None)
        if con is not None:
            self._local.con = None
            con.close()

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        return self.connection.execute(sql, params)

    def one(self, sql: str, params=()) -> Optional[sqlite3.Row]:
        return self.execute(sql, params).fetchone()

    def all(self, sql: str, params=()):
        return self.execute(sql, params).fetchall()

    def transaction(self):
        '''One atomic write. ``BEGIN IMMEDIATE`` takes the write lock before
        the first read, which a deferred ``BEGIN`` would fail to upgrade.'''
        return _Transaction(self.connection)


class _Transaction:
    def __init__(self, con: sqlite3.Connection):
        self._con = con

    def __enter__(self) -> sqlite3.Connection:
        self._con.execute("BEGIN IMMEDIATE")
        return self._con

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._con.execute("COMMIT" if exc_type is None else "ROLLBACK")
        return False
