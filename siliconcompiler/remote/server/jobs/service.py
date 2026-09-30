'''
The job service: one deployment's jobs, composed from one part per step
of a job's life.
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
    '''One deployment's jobs.

    Built once and held on the app, because it owns the dispatcher -- which for
    a local deployment holds the handles to the processes it started.
    '''

    def __init__(self, store, config, storage, dispatcher, datadir):
        self._store = store
        self._config = config
        self._storage = storage
        self._dispatcher = dispatcher
        self._datadir = Path(datadir)

        # Per job, the last time this process asked the scheduler anything.
        self._asked = {}

        # This server's own copies of remote sources, fetched only from the
        # allowlist, and what answers "can you supply this" by identity.
        import threading

        from siliconcompiler.remote.server.staging import allowlist
        from siliconcompiler.remote.server.staging.sources import SourceStore

        self._sources = SourceStore(
            self._datadir,
            [allowlist.parse(entry) for entry in (config["fetch_allowlist"] or [])])
        self._supply = _Supply(config, self._sources)

        # The jobs whose sources are being fetched in this process, so a
        # restart can tell one still in hand from one it has to pick up again.
        self._preparing = set()
        self._preparing_lock = threading.Lock()

        # One environment build per key at a time in this process: two jobs
        # asking for the same set wait for one build, and the second reuses it.
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

    def builds_root(self, user_id: str) -> Path:
        return self.user_root(user_id) / "builds"

    def cache_dir(self, user_id: str) -> Path:
        return self.user_root(user_id) / "cache"

    def container_mounts(self):
        '''What every container this deployment runs must be able to see,
        whoever's job it is: whatever the cluster needs named -- the munge
        socket and slurm.conf on Slurm, since a framework image submits the
        nodes of the flow it is driving. Baked into each shared bundle.

        🔴 **Never the data directory.** It holds the token signing key and the
        store, and every user's tree (profile §0). What one job sees is
        :meth:`job_mounts`, in a bundle of its own.
        '''
        return [str(path) for path in (self._config["container_mounts"] or [])]

    def job_mounts(self, job):
        '''What one job's node containers see: the job's own tree and its
        user's cache read-write, and the roots this server supplies read-only.
        '''
        # 🔴 Supplied roots are READ-ONLY in the job: the held copies of remote
        # sources and every private root the operator maps. A job reads what it
        # is supplied and can change none of it -- the next job gets the same
        # copy.
        #
        # ⚠️ **Every source a bundle binds must exist**, or the runtime cannot
        # start the container at all ("cannot stat"): this server's own
        # directories are made here, and an operator's root that is not there
        # is left out, and said -- a job cannot be supplied from it anyway.
        own = [self.job_root(job["user_id"], job["id"]), self.cache_dir(job["user_id"]),
               self._datadir / "sources"]
        for path in own:
            path.mkdir(parents=True, exist_ok=True)
        private = []
        for roots in (self._config["private_dataroots"] or {}).values():
            for root in roots.values():
                if os.path.isdir(root):
                    private.append((str(root), "ro"))
                else:
                    logger.warning(f"private dataroot {root} is not a directory here; "
                                   "no container is given it")
        return [(str(own[0]), "rw"), (str(own[1]), "rw"), (str(own[2]), "ro")] + private

    def framework_mounts(self, job):
        '''What the job's own process sees, beside :meth:`job_mounts`: where
        it unpacks the images its nodes run in, and where it writes their
        bundles, which no node sees.'''
        return self.job_mounts(job) + [(str(self.bundles_root()), "rw"),
                                       (str(self.job_bundles(job["id"])), "rw")]

    def job_bundles(self, job_id: str) -> Path:
        '''Where one job's bundles are: outside its tree, so that no node of
        it can rewrite what the next is started with.'''
        return self._datadir / "jobbundles" / job_id

    def bundles_root(self) -> Path:
        '''Where unpacked container images live.

        🔴 Beside the store rather than under a user's tree, which is the one
        place in this layout that is deliberately NOT per user. A bundle is a
        read-only root filesystem identical for everybody who runs that digest,
        so per-user copies would buy nothing and cost a copy of every tool image
        per user -- the one number decision 3 accepted for the cache and would
        not accept twice.
        '''
        return self._datadir / "images"

    def job_root(self, user_id: str, job_id: str) -> Path:
        '''The build directory for one job of one user.

        Per user as well as per job. The ownership record is `jobs.user_id`, in
        the store, rather than a file inside the directory it protects -- which
        is what the tree it replaces did.
        '''
        return self.builds_root(user_id) / job_id
