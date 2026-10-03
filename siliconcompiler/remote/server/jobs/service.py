'''
The job service: one deployment's jobs, one mixin per step of a job's life.
'''

import os

from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import _Supply, logger
from siliconcompiler.remote.server.jobs.continuations import ContinuationsMixin
from siliconcompiler.remote.server.jobs.create import CreateMixin
from siliconcompiler.remote.server.jobs.dispatching import DispatchMixin
from siliconcompiler.remote.server.jobs.lifecycle import LifecycleMixin
from siliconcompiler.remote.server.jobs.pythonenv import PythonEnvMixin
from siliconcompiler.remote.server.jobs.reconcile import ReconcileMixin
from siliconcompiler.remote.server.jobs.results import ResultsMixin
from siliconcompiler.remote.server.jobs.rows import RowsMixin
from siliconcompiler.remote.server.jobs.staging import StagingMixin
from siliconcompiler.remote.server.jobs.submit import SubmitMixin


class JobService(CreateMixin, ContinuationsMixin, SubmitMixin, StagingMixin, PythonEnvMixin,
                 DispatchMixin, LifecycleMixin, ReconcileMixin, ResultsMixin, RowsMixin):
    '''One deployment's jobs, built once and held on the app: it owns the
    dispatcher, which locally holds the processes it started.'''

    def __init__(self, store, config, storage, dispatcher, datadir):
        self._store = store
        self._config = config
        self._storage = storage
        self._dispatcher = dispatcher
        self._datadir = Path(datadir)

        # Per job, the last time this process asked the scheduler anything.
        self._asked = {}

        # Held copies of remote sources, and what answers "can you supply this".
        import threading

        from siliconcompiler.remote.server.staging import allowlist
        from siliconcompiler.remote.server.staging.sources import SourceStore

        self._sources = SourceStore(
            self._datadir,
            [allowlist.parse(entry) for entry in (config["fetch_allowlist"] or [])])
        self._supply = _Supply(config, self._sources)

        # Jobs being staged in this process, so a restart can tell one in hand
        # from one to pick up again.
        self._preparing = set()
        self._preparing_lock = threading.Lock()
        # Each staging pass's `max_staging_seconds` deadline, by
        # `time.monotonic()`, set as it starts (surface D294).
        self._staging_deadlines: Dict[str, float] = {}

        # One environment build per key at a time; a second asker reuses it.
        self._building: Dict[str, Any] = {}
        self._building_lock = threading.Lock()
        # How a build is waited on -- `envbuild.wait_for`'s pacing.
        self._build_wait: Dict[str, float] = {}

        # Keyed requests being handled now, so a retry of one gets `in_progress`.
        self._in_flight: Set[Tuple[str, str, str]] = set()
        self._in_flight_lock = threading.Lock()

    def _keyed(self, user_id: str, what: str, key: Optional[str]):
        '''While a keyed request is handled; a retry meanwhile is refused
        `in_progress`, with `Retry-After`, and binds nothing.'''
        import contextlib

        if key is None:
            return contextlib.nullcontext()

        @contextlib.contextmanager
        def held():
            token = (user_id, what, key)
            with self._in_flight_lock:
                if token in self._in_flight:
                    raise ProblemError(
                        "job-state-conflict", reason="in_progress",
                        detail="a request with this Idempotency-Key is still being handled",
                        headers={"Retry-After": "1"})
                self._in_flight.add(token)
            try:
                yield
            finally:
                with self._in_flight_lock:
                    self._in_flight.discard(token)
        return held()

    ######################################################################
    # Where a user's work lives
    ######################################################################

    def user_root(self, user_id: str) -> Path:
        return self._datadir / "users" / user_id

    def cache_dir(self, user_id: str) -> Path:
        return self.user_root(user_id) / "cache"

    def container_mounts(self):
        '''What every container must see, whoever's job it is; baked into each
        shared bundle.

        🔴 Never the data directory: it holds the signing key, the store and
        every user's tree (profile §0). One job's own is :meth:`job_mounts`.
        '''
        return [str(path) for path in (self._config["container_mounts"] or [])]

    def job_mounts(self, job):
        '''What one job's node containers see: its tree and its user's cache
        read-write, and the roots this server supplies read-only.
        '''
        # 🔴 Supplied roots are READ-ONLY: the next job gets the same copy.
        # ⚠️ Every bound source must exist or the container cannot start, so
        # this server's own are made here and a missing operator root is left
        # out, and said.
        own = [self.job_root(job["user_id"], job["id"]), self.cache_dir(job["user_id"]),
               self._datadir / "sources"]
        for path in own:
            path.mkdir(parents=True, exist_ok=True)
        from siliconcompiler.remote.server.config import private_paths

        private = []
        for root in private_paths(self._config["private_dataroots"] or {}):
            if os.path.isdir(root):
                private.append((str(root), "ro"))
            else:
                logger.warning(f"private dataroot {root} is not a directory here; "
                               "no container is given it")
        return [(str(own[0]), "rw"), (str(own[1]), "rw"), (str(own[2]), "ro")] + private

    def framework_mounts(self, job):
        '''What the job's own process sees, beside :meth:`job_mounts`: the
        unpacked images and its nodes' bundles, which no node sees.'''
        return self.job_mounts(job) + [(str(self.bundles_root()), "rw"),
                                       (str(self.job_bundles(job["id"])), "rw")]

    def job_bundles(self, job_id: str) -> Path:
        '''Where one job's bundles are: outside its tree, so no node can
        rewrite what the next is started with.'''
        return self._datadir / "jobbundles" / job_id

    def bundles_root(self) -> Path:
        '''Where unpacked container images live.

        🔴 Deliberately NOT per user, the one place in this layout: a bundle is
        identical for everyone running that digest, and per-user copies would
        cost every tool image per user (decision 3).
        '''
        return self._datadir / "images"

    def job_root(self, user_id: str, job_id: str) -> Path:
        '''The build directory for one job of one user. Ownership is
        `jobs.user_id`, not a file inside the directory it protects.'''
        return self.user_root(user_id) / "builds" / job_id
