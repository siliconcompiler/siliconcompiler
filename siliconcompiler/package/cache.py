"""
Central store for resolved data source paths.

Resolving a data source can be expensive: a remote data source may involve a
network download of an entire git repository or archive. :class:`PathCache`
gives a run one place to record

* the local path a data source resolved to, so it is only ever resolved once,
* how many times resolving it has *failed*, so a source that cannot be fetched
  is retried a bounded number of times -- with a randomized, exponentially
  growing delay between attempts -- and then abandoned with an actionable error
  rather than re-downloaded by every caller, and
* the per-source download mutex used to keep threads from fetching the same
  source concurrently.

There is one cache per process, owned by
:class:`~siliconcompiler.utils.multiprocessing.MPManager` alongside the other
shared resources and reachable through
:meth:`~siliconcompiler.utils.multiprocessing.MPManager.get_path_cache`. Entries
are keyed by a content hash of the source URI and its reference, so a single
cache serves every project, library and design in the process: the same source
at the same reference always resolves to the same path, and the number of
entries is bounded by how many distinct sources a run touches.

A ``fork`` worker inherits the cache as it stood when the worker was launched. A
worker that cannot inherit it -- a ``spawn`` worker, or a node run out of
process by the docker or slurm scheduler -- starts empty and reports what it
resolved back to its parent, through :meth:`export` and :meth:`seed`.
"""

import math
import random
import threading
import time

from typing import Any, Dict, Optional, Tuple, Union

from pathlib import Path


class DataRootResolutionError(RuntimeError):
    """
    Raised when a data source could not be resolved within its attempt budget.

    Once a source has failed :attr:`PathCache.max_attempts` times, further
    attempts are abandoned and this error is raised instead of retrying, so a
    broken or unreachable data source cannot be re-fetched indefinitely.
    """


class PathCache:
    """
    Cache of resolved data source paths and resolution failures.

    Entries are keyed by a resolver's ``cache_id`` (a hash of the source URI and
    its reference), so the same source shares one entry no matter which name it
    was registered under, which schema asked for it, or how many resolver objects
    are built for it.

    Obtain the process cache with
    :meth:`~siliconcompiler.utils.multiprocessing.MPManager.get_path_cache`
    rather than constructing one.
    """

    #: Number of times a data source may fail to resolve before it is abandoned.
    DEFAULT_MAX_ATTEMPTS: int = 3

    #: Delay, in seconds, before the first retry of a failed source.
    DEFAULT_RETRY_DELAY: float = 2.0

    #: Factor each successive retry delay is multiplied by. With the default
    #: delay this gives a ladder of roughly 2s, 5s, 10s, 23s, ...
    DEFAULT_RETRY_BACKOFF: float = 2.25

    #: Fraction the delay is randomly varied by, either side of its nominal
    #: value. Spreads out workers that failed together instead of letting them
    #: all retry the same unreachable source at the same moment.
    RETRY_JITTER: float = 0.25

    #: Ceiling on any single delay, so a large attempt budget cannot turn the
    #: growing backoff into an effectively unbounded wait.
    RETRY_MAX_DELAY: float = 60.0

    def __init__(self):
        self.__paths: Dict[str, str] = {}
        self.__failures: Dict[str, Tuple[int, str]] = {}
        self.__max_attempts: int = PathCache.DEFAULT_MAX_ATTEMPTS
        self.__retry_delay: float = PathCache.DEFAULT_RETRY_DELAY
        self.__retry_backoff: float = PathCache.DEFAULT_RETRY_BACKOFF

        self.__lock = threading.RLock()
        self.__download_locks: Dict[str, threading.Lock] = {}

    # ------------------------------------------------------------------
    # Resolved paths
    # ------------------------------------------------------------------
    def get(self, cache_id: str) -> Optional[str]:
        """
        Returns the cached path for a data source.

        Args:
            cache_id (str): The resolver cache ID of the data source.

        Returns:
            str or None: The resolved path, or None if it is not cached.
        """
        with self.__lock:
            return self.__paths.get(cache_id, None)

    def set(self, cache_id: str, path: Union[str, Path]) -> None:
        """
        Records the path a data source resolved to.

        Args:
            cache_id (str): The resolver cache ID of the data source.
            path: The local path the source resolved to.
        """
        with self.__lock:
            self.__paths[cache_id] = str(path)

    # ------------------------------------------------------------------
    # Failure tracking
    # ------------------------------------------------------------------
    def attempts(self, cache_id: str) -> int:
        """
        Returns how many times resolving a data source has failed.

        Args:
            cache_id (str): The resolver cache ID of the data source.

        Returns:
            int: The number of recorded failures.
        """
        with self.__lock:
            attempts, _ = self.__failures.get(cache_id, (0, ""))
            return attempts

    def failure(self, cache_id: str) -> Optional[str]:
        """
        Returns the last recorded failure for a data source.

        Args:
            cache_id (str): The resolver cache ID of the data source.

        Returns:
            str or None: The last error, formatted as ``"<class>: <message>"``,
                or None if the source has not failed.
        """
        with self.__lock:
            if cache_id not in self.__failures:
                return None
            return self.__failures[cache_id][1]

    def is_exhausted(self, cache_id: str) -> bool:
        """
        Returns True if a data source has used up its attempt budget.

        Args:
            cache_id (str): The resolver cache ID of the data source.

        Returns:
            bool: True if the source has failed :attr:`max_attempts` times.
        """
        return self.attempts(cache_id) >= self.max_attempts

    def record_failure(self, cache_id: str, error: BaseException) -> int:
        """
        Records a failed attempt at resolving a data source.

        The error is stored as text rather than as an exception object so that
        the cache stays picklable and can be handed between processes.

        Args:
            cache_id (str): The resolver cache ID of the data source.
            error (BaseException): The error that caused the failure.

        Returns:
            int: The total number of failures recorded for this source.
        """
        with self.__lock:
            attempts, _ = self.__failures.get(cache_id, (0, ""))
            attempts += 1
            self.__failures[cache_id] = (attempts, f"{type(error).__name__}: {error}")
            return attempts

    def clear_failure(self, cache_id: str) -> None:
        """
        Forgets any recorded failures for a data source.

        Args:
            cache_id (str): The resolver cache ID of the data source.
        """
        with self.__lock:
            self.__failures.pop(cache_id, None)

    # ------------------------------------------------------------------
    # Retry policy
    # ------------------------------------------------------------------
    @property
    def max_attempts(self) -> int:
        """int: Times a data source may fail to resolve before being abandoned."""
        with self.__lock:
            return self.__max_attempts

    def set_max_attempts(self, value: int) -> None:
        """
        Sets how many times a data source may fail before being abandoned.

        Args:
            value (int): The maximum number of attempts. Must be at least 1.

        Raises:
            TypeError: If ``value`` is not a number.
            ValueError: If ``value`` is less than 1.
        """
        try:
            value = int(value)
        except (TypeError, ValueError) as e:
            raise type(e)(f"max_attempts must be an integer: {value!r}") from e
        if value < 1:
            raise ValueError("max_attempts must be greater than 0")
        with self.__lock:
            self.__max_attempts = value

    @property
    def retry_delay(self) -> float:
        """float: Delay, in seconds, before the first retry of a failed source."""
        with self.__lock:
            return self.__retry_delay

    def set_retry_delay(self, value: float) -> None:
        """
        Sets the delay applied before the first retry of a failed data source.

        Later retries grow from this by :attr:`retry_backoff`.

        Args:
            value (float): The delay in seconds. Zero disables waiting.

        Raises:
            TypeError: If ``value`` is not a number.
            ValueError: If ``value`` is negative, infinite, or not a number.
        """
        try:
            value = float(value)
        except (TypeError, ValueError) as e:
            raise type(e)(f"retry_delay must be a number: {value!r}") from e
        # nan and inf slip past a plain "< 0" test and would either wait forever
        # or make time.sleep() raise from inside path resolution.
        if not math.isfinite(value):
            raise ValueError("retry_delay must be finite")
        if value < 0:
            raise ValueError("retry_delay must not be negative")
        with self.__lock:
            self.__retry_delay = value

    @property
    def retry_backoff(self) -> float:
        """float: Factor each successive retry delay is multiplied by."""
        with self.__lock:
            return self.__retry_backoff

    def set_retry_backoff(self, value: float) -> None:
        """
        Sets how sharply the retry delay grows with each failure.

        Args:
            value (float): The multiplier applied per retry. Must be at least 1;
                exactly 1 keeps every delay at :attr:`retry_delay`.

        Raises:
            TypeError: If ``value`` is not a number.
            ValueError: If ``value`` is less than 1, or is not finite.
        """
        try:
            value = float(value)
        except (TypeError, ValueError) as e:
            raise type(e)(f"retry_backoff must be a number: {value!r}") from e
        if not math.isfinite(value):
            raise ValueError("retry_backoff must be finite")
        if value < 1:
            raise ValueError("retry_backoff must be at least 1")
        with self.__lock:
            self.__retry_backoff = value

    def next_retry_delay(self, cache_id: str) -> float:
        """
        Returns how long to wait before the next attempt at a data source.

        The delay grows exponentially with the number of failures already
        recorded -- roughly 2s, 5s, 10s with the default settings -- and is
        randomly varied by :attr:`RETRY_JITTER` either side of that. The jitter
        matters as much as the growth: without it, workers that failed together
        stay in lockstep and keep hammering the same unreachable source in
        unison. Any single delay is capped at :attr:`RETRY_MAX_DELAY`.

        Args:
            cache_id (str): The resolver cache ID of the data source.

        Returns:
            float: Seconds to wait. Zero for a source that has not failed yet,
                or when the delay has been configured away.
        """
        attempts = self.attempts(cache_id)
        if not attempts:
            return 0.0

        with self.__lock:
            base = self.__retry_delay
            backoff = self.__retry_backoff

        if base <= 0:
            return 0.0

        nominal = base * (backoff ** (attempts - 1))
        jitter = PathCache.RETRY_JITTER
        delay = random.uniform(nominal * (1 - jitter), nominal * (1 + jitter))

        return min(delay, PathCache.RETRY_MAX_DELAY)

    def wait_before_retry(self, cache_id: str) -> None:
        """
        Waits before retrying a data source that has already failed.

        This is the only place a retry delay is applied. Individual resolvers
        make a single attempt per call and never sleep themselves, so backoff
        policy lives here rather than being reimplemented per data source type.
        A source that has not failed yet is never delayed.

        Args:
            cache_id (str): The resolver cache ID of the data source.
        """
        delay = self.next_retry_delay(cache_id)
        if delay > 0:
            time.sleep(delay)

    # ------------------------------------------------------------------
    # Central seeding and export
    # ------------------------------------------------------------------
    def export(self) -> Dict[str, Any]:
        """
        Returns a serializable snapshot of the cache contents.

        The result contains only strings and integers, so it can be sent over a
        pipe or written to a command line.

        Returns:
            dict: A payload accepted by :meth:`seed`.
        """
        with self.__lock:
            return {
                "paths": dict(self.__paths),
                "failures": {key: list(value) for key, value in self.__failures.items()}
            }

    def seed(self, payload: Optional[Dict[str, Any]], include_failures: bool = True) -> None:
        """
        Merges a snapshot produced by :meth:`export` into this cache.

        Resolved paths are always merged. Failures are merged only when
        ``include_failures`` is True; a caller that considers failures local to
        the process that saw them (for example a scheduler merging results from
        one node, where the next node may well succeed) can leave them behind.

        A snapshot arrives from another process, over a pipe or a command line,
        so every part of it is treated as untrusted: anything unrecognized is
        skipped rather than raising, because a garbled message must never take
        down the run that received it.

        Args:
            payload (dict): A snapshot from :meth:`export`. Ignored if it is not
                a dictionary, so a truncated or unexpected message is harmless.
            include_failures (bool): If True, also merge recorded failures.
        """
        if not isinstance(payload, dict):
            return

        paths = payload.get("paths", None)
        with self.__lock:
            if isinstance(paths, dict):
                for key, value in paths.items():
                    if isinstance(key, str) and value is not None:
                        self.__paths[key] = str(value)

            if not include_failures:
                return

            failures = payload.get("failures", None)
            if not isinstance(failures, dict):
                return

            for key, value in failures.items():
                if not isinstance(key, str):
                    continue
                # Accept only a real two-element sequence. A bare string would
                # happily unpack into two characters, so reject anything that is
                # not a list or tuple before looking at it.
                if not isinstance(value, (list, tuple)) or len(value) != 2:
                    continue
                try:
                    attempts = int(value[0])
                except (TypeError, ValueError):
                    continue
                attempts = max(0, attempts)
                # Keep whichever side has seen more failures so a merge can only
                # ever tighten the remaining budget.
                known, _ = self.__failures.get(key, (0, ""))
                if attempts >= known:
                    self.__failures[key] = (attempts, str(value[1]))

    def clear(self) -> None:
        """Removes all cached paths and recorded failures."""
        with self.__lock:
            self.__paths.clear()
            self.__failures.clear()

    # ------------------------------------------------------------------
    # Download mutex
    # ------------------------------------------------------------------
    def thread_lock(self, cache_id: str) -> threading.Lock:
        """
        Returns the download lock for a data source, creating it if needed.

        The lock is keyed by ``cache_id`` so it has the same granularity as the
        inter-process lock file: threads fetching the same source contend, and
        threads fetching unrelated sources do not.

        Args:
            cache_id (str): The resolver cache ID of the data source.

        Returns:
            threading.Lock: The lock guarding this source.
        """
        with self.__lock:
            if cache_id not in self.__download_locks:
                self.__download_locks[cache_id] = threading.Lock()
            return self.__download_locks[cache_id]

    def __repr__(self) -> str:
        with self.__lock:
            return (f"{type(self).__name__}(paths={len(self.__paths)}, "
                    f"failures={len(self.__failures)}, "
                    f"max_attempts={self.__max_attempts})")
