"""
This module defines the core path resolution system for SiliconCompiler packages.

It provides a flexible mechanism to locate data sources, whether they are on
the local filesystem, remote servers, or part of a Python package. The system
is designed to be extensible, allowing new resolver types to be added as plugins.
It also includes robust caching and locking mechanisms for handling remote data
efficiently and safely in multi-process and multi-threaded environments.
"""
import contextlib
import functools
import importlib
import json
import logging
import os
import random
import re
import site
import shutil
import stat
import tarfile
import time
import threading

import os.path

from typing import Callable, NamedTuple, Optional, List, Dict, Tuple, Type, Union, \
    TYPE_CHECKING

from pathlib import Path, PureWindowsPath

from siliconcompiler.package.cache import PathCache, DataRootResolutionError, \
    PermanentResolutionError
from siliconcompiler.utils import UnsafeArchiveError, get_plugins
from siliconcompiler.utils.paths import cwdirsafe, datarootdir
from siliconcompiler.utils.multiprocessing import MPManager, FileLockTimeout, \
    get_file_lock

if TYPE_CHECKING:
    from urllib import parse as url_parse

    from siliconcompiler.project import Project
    from siliconcompiler.schema_support.pathschema import PathSchema
    from siliconcompiler.schema import BaseSchema


#: The extraction filters, and so the errors they raise, only exist on Python
#: releases carrying the PEP 706 backport.
_TAR_FILTER_ERRORS: Tuple[Type[BaseException], ...] = \
    (tarfile.FilterError,) if hasattr(tarfile, "FilterError") else ()


#: Registry key marking resolver population as *complete*, written only once
#: every scheme is in place.
#:
#: The registry cannot use "the category is non-empty" as its populated test:
#: the category becomes non-empty on the very first write, so a caller could
#: return early believing the registry was ready and then fail to find a scheme
#: that had not been registered yet. The remote schemes (``https``, ``git``,
#: ``github``, ``scp``) are registered last and so had the widest exposure,
#: which is why an ordinary GitHub tarball could be reported as an unsupported
#: URI while a ``file://`` path never was.
#:
#: Other threads are kept out by holding the category (see
#: :meth:`~siliconcompiler.utils.settings.SettingsManager.lock_category`), but
#: the marker is what a *forked child* has to go on: it inherits whatever the
#: registry held at the instant of the fork, with no lock left to wait on.
#:
#: The leading underscores keep the marker out of the scheme namespace:
#: :func:`urllib.parse.urlparse` only recognises a scheme that starts with a
#: letter, so no source URI can ever resolve to this key.
_RESOLVERS_POPULATED: str = "__populated__"


class FetchPolicy(NamedTuple):
    """
    How a remote resolver may reach the network, for a caller fetching on
    somebody else's behalf -- a server resolving a job's sources.

    Attributes:
        check_url: called with every URL a resolver is about to contact, and
            raises :class:`FetchRefused` to refuse it.
        home: an empty directory, used as ``HOME`` for the tools a resolver
            runs, so no user configuration or credential file is read.
        proxy: an HTTP proxy every subprocess connects through, which applies
            the same rules to what the resolver cannot see -- a git redirect,
            an LFS object's storage URL.
        timeout: seconds one request or command may take.
        max_bytes: the most one download may weigh.
    """
    check_url: Callable[[str], None]
    home: str
    proxy: Optional[str] = None
    timeout: Optional[float] = None
    max_bytes: Optional[int] = None


class FetchRefused(PermanentResolutionError):
    """A URL the active :class:`FetchPolicy` does not let a resolver contact."""


_FETCH_POLICY = threading.local()


@contextlib.contextmanager
def fetch_policy(policy: FetchPolicy):
    """
    Resolve remote sources on this thread under ``policy``.

    Inside it a remote resolver sends no credential of any kind -- no token
    from the environment, no credential in the URL, no credential helper, no
    SSH agent or key -- reaches only ``https``, and passes every URL it
    contacts to ``policy.check_url`` first. Per thread, and nestable.
    """
    previous = getattr(_FETCH_POLICY, "policy", None)
    _FETCH_POLICY.policy = policy
    try:
        yield policy
    finally:
        _FETCH_POLICY.policy = previous


def current_fetch_policy() -> Optional[FetchPolicy]:
    """The :class:`FetchPolicy` active on this thread, or None."""
    return getattr(_FETCH_POLICY, "policy", None)


class Resolver:
    """
    Abstract base class for all data source resolvers.

    This class defines the common interface for locating and accessing data
    from various sources. It includes a caching mechanism to avoid redundant
    resolutions within a single run.

    Attributes:
        name (str): The name of the data package being resolved.
        schema (object): The root object (typically a Project) providing context,
            such as environment variables and the working directory.
        source (str): The URI or path specifying the data source.
        reference (str): A version, commit hash, or tag for remote sources.
    """

    def __init__(self, name: str,
                 schema: Optional[Union["Project", "BaseSchema"]],
                 source: str,
                 reference: Optional[str] = None):
        """
        Initializes the Resolver.
        """
        self.__name = name
        self.__schema = schema
        self.__root = None if schema is None else schema._parent(root=True)
        self.__source = source
        self.__reference = reference
        self.__changed = False
        self.__cacheid = None
        self.__collectionid = None
        self.__private = False

        # The marker comes off the source, which is then fetched by its plain
        # scheme; is_private is all that keeps it, and says what it means.
        scheme = self.urlscheme
        if scheme.endswith("+private"):
            self.__private = True
            _, separator, remainder = self.__source.partition(":")
            self.__source = f"{scheme.removesuffix('+private')}{separator}{remainder}"

        if self.__root and hasattr(self.__root, "logger"):
            rootlogger = self.__root.logger
        else:
            rootlogger = MPManager.logger()
        self.__logger = rootlogger.getChild(f"resolver-{self.name}")

    @staticmethod
    def populate_resolvers() -> None:
        """
        Scans for and registers all available resolver plugins.

        This method populates the internal `_RESOLVERS` dictionary with both
        built-in resolvers (file, key, python, http, git, github, gitlab, scp) and any
        resolvers provided by external plugins. Built-ins are registered first,
        so a plugin claiming the same scheme takes precedence.

        Population is atomic. Several threads reach here at once whenever a
        process resolves data sources in parallel, so the registry is held for
        the length of the build and a thread that arrives mid-population waits
        rather than looking up a scheme that is registered but not yet written
        (see :data:`_RESOLVERS_POPULATED`).
        """
        # Imported here because each of these modules imports RemoteResolver from
        # this module.
        from siliconcompiler.package import git, github, gitlab, https, scp

        settings = MPManager().get_transient_settings()
        with settings.lock_category("resolvers"):
            if settings.get("resolvers", _RESOLVERS_POPULATED, False):
                # Already populated
                return

            settings.set("resolvers", "", FileResolver)
            settings.set("resolvers", "file", FileResolver)
            settings.set("resolvers", "key", KeyPathResolver)
            settings.set("resolvers", "python", PythonPathResolver)
            settings.set("resolvers", "dataroot", DatarootResolver)

            settings.set("resolvers", "file+private", FileResolver)

            builtins = (https.get_resolver, git.get_resolver, github.get_resolver,
                        gitlab.get_resolver, scp.get_resolver)
            for resolver in (*builtins, *get_plugins("path_resolver")):
                for scheme, res in resolver().items():
                    settings.set("resolvers", scheme, res)

            # Written last, once the registry above is complete.
            settings.set("resolvers", _RESOLVERS_POPULATED, True)

    @staticmethod
    def find_resolver(source: str) -> Type["Resolver"]:
        """
        Finds the appropriate resolver class for a given source URI.

        The resolver registered for the source's scheme is asked for the one to
        use (:meth:`subresolver`), so a scheme can hand one host's URLs to a
        more specific class.

        Args:
            source (str): The source URI (e.g., 'file:///path/to/file', 'git://...').

        Returns:
            Resolver: The resolver class capable of handling the source.

        Raises:
            ValueError: If no suitable resolver is found for the URI scheme.
        """
        if os.path.isabs(source):
            return FileResolver

        Resolver.populate_resolvers()

        # Imported here rather than at module scope: urllib.parse costs ~1.2 ms
        # (it pulls ipaddress) and only URI-shaped sources reach it.
        from urllib import parse as url_parse

        url = url_parse.urlparse(source)
        settings = MPManager().get_transient_settings()
        resolver = settings.get("resolvers", url.scheme, None)
        if resolver:
            return resolver.subresolver(url)

        raise ValueError(f"Source URI '{source}' is not supported")

    @classmethod
    def subresolver(cls, url: "url_parse.ParseResult") -> Type["Resolver"]:
        """
        The resolver to use for ``url``, which :meth:`find_resolver` asks the
        resolver registered for the scheme.

        The base is that resolver itself. A scheme whose URLs need handling per
        host overrides this to hand those hosts to a more specific class: an
        archive on ``github.com`` is still ``https``, but GitHub's resolver
        handles it.

        Args:
            url (urllib.parse.ParseResult): The parsed source URI.

        Returns:
            type: The resolver class to use.
        """
        return cls

    @property
    def name(self) -> str:
        """The name of the data package being resolved."""
        return self.__name

    @property
    def display_name(self) -> str:
        """A user-friendly display name for the resolver."""
        if self.__schema:
            keypath = self.__schema._keypath
            if keypath:
                return f"{self.name} [{','.join(keypath)}]"
        return self.name

    @property
    def is_retryable(self) -> bool:
        """
        True if a failed resolution is worth retrying.

        Failures are then counted in the shared cache, delayed with a growing
        backoff, and abandoned once the budget runs out. Only worth doing where an
        attempt is expensive, so remote sources enable it (see
        :class:`RemoteResolver`) while local ones leave it off: they fail
        instantly and identically every time, so a retry cannot help.
        """
        return False

    @property
    def is_private(self) -> bool:
        """
        True if the source was registered with a ``+private`` scheme:
        ``file+private://``, ``git+ssh+private://``, ``github+private://`` and
        the rest.

        The marker says two things:

        * Fetching the source needs the user's own access, so a resolver goes
          straight to its authenticated route: ``github://`` skips its public
          lookup.
        * The source must never leave this machine. A remote run is not to
          upload it, so the server has to supply its own copy under the same
          names, or refuse the job.

        The second is the one to decide by. A private repository that this
        machine can fetch needs no marker: unmarked, a remote run can fetch it
        here and send it, while marked, the run depends on the server already
        holding it.
        """
        return self.__private

    def is_permanent_failure(self, error: BaseException) -> bool:
        """
        True if ``error`` will recur identically however many times it is retried.

        The attempt budget is for failures a second try might survive: a dropped
        connection, a truncated transfer, a server having a bad minute. It is
        wasted on a failure that is settled the moment it happens, and the waste
        is not free -- abandoning a source takes
        :attr:`PathCache.max_attempts` fetches of the same data, plus the backoff
        between them, to arrive at the answer the first attempt already had.

        Two kinds of error are treated as settled:

        * :class:`~siliconcompiler.package.cache.PermanentResolutionError`, raised
          by a resolver that has itself established the answer will not change --
          an HTTP status saying the data is not there, for instance.
        * ``tarfile.FilterError``, raised when the extraction filter refuses a
          member of a downloaded archive, and
          :class:`~siliconcompiler.utils.UnsafeArchiveError`, its equivalent
          where the interpreter has no filter. That verdict is a property of the
          archive's contents, so a fresh copy of the same archive earns it again.

        Anything else counts as transient, deliberately: this decides how much
        effort a failure is worth, and treating a retryable error as settled costs
        a run that would have recovered, while the reverse costs some bandwidth.
        Subclasses may widen this for errors specific to how they fetch.

        Args:
            error (BaseException): The error a resolution attempt raised.

        Returns:
            bool: True if the source should be abandoned without further attempts.
        """
        return isinstance(error, (PermanentResolutionError, UnsafeArchiveError,
                                  *_TAR_FILTER_ERRORS))

    @property
    def is_indirect(self) -> bool:
        """
        True if this resolver is an indirection rather than a location of its own.

        ``dataroot://name`` and ``key://keypath`` do not name data; they name
        something *within a schema* that in turn names data, and they hand the
        real work to that resolver. Two consequences follow, both applied by
        :meth:`get_path`:

        * An indirection is not cached. The cache is keyed by :attr:`cache_id`, a
          hash of the source URI and reference, which identifies a path only for a
          source that means the same thing everywhere -- an absolute ``file://``
          path, a ``python://`` module, a remote URL at a fixed reference. A
          dataroot name or a keypath means something different in every project or
          design, so caching one would let two schemas collide and hand each other
          the wrong path. Resolving an indirection is cheap, and where it points
          at an expensive source that resolver still caches.
        * An indirection does not announce where data was found, because the
          resolver it delegates to already reported the same location.
        """
        return False

    @property
    def root(self) -> Optional[Union["Project", "BaseSchema"]]:
        """The root object (e.g., Project) providing context."""
        return self.__root

    @property
    def schema(self) -> Optional["BaseSchema"]:
        """The schema object (e.g., Project) providing context."""
        return self.__schema

    @property
    def logger(self) -> logging.Logger:
        """The logger instance for this resolver."""
        return self.__logger

    @property
    def source(self) -> str:
        """The URI or path specifying the data source."""
        return self.__source

    @staticmethod
    def _masked_query(query: str) -> str:
        """
        A URL query with every value replaced by ``***`` and every name kept.

        A field with no ``=`` is masked whole: it may be a flag, but a bare token
        (``?<token>``) looks the same. ``;`` separates fields as ``&`` does, since
        some servers read it that way, and a token ahead of one would otherwise
        pass as part of a name.
        """
        fields = re.split(r"([&;])", query)
        for n, field in enumerate(fields):
            if field in ("", "&", ";"):
                continue
            name, separator, _ = field.partition("=")
            fields[n] = f"{name}=***" if separator else "***"
        return "".join(fields)

    @staticmethod
    def _masked_uri(url: str, show_userinfo: bool = True) -> str:
        """
        ``url`` with its credentials masked and everything else as written: the
        userinfo shown as ``***``, or dropped if ``show_userinfo`` is False, and
        every query value as ``***`` (see :meth:`_masked_query`).
        """
        from urllib import parse as url_parse
        parts = url_parse.urlsplit(url)
        if "@" not in parts.netloc and not parts.query:
            return url

        auth = ""
        if show_userinfo and (parts.username or parts.password):
            user = "***" if parts.username else ""
            pwd = ":***" if parts.password else ""
            auth = f"{user}{pwd}@"
        host = parts.netloc.rpartition("@")[2]

        # Joined by hand: urlunsplit drops the '//' ahead of an empty host under
        # a scheme it does not know, so 'source:///x' would come back 'source:/x'.
        masked = f"{parts.scheme}:" if parts.scheme else ""
        after_scheme = url.lstrip().partition(":")[2] if parts.scheme else url.lstrip()
        if after_scheme.startswith("//"):
            masked += f"//{auth}{host}"
        masked += parts.path
        if parts.query:
            masked += f"?{Resolver._masked_query(parts.query)}"
        if parts.fragment:
            masked += f"#{parts.fragment}"
        return masked

    @property
    def source_print(self) -> str:
        """The source URI with sensitive information masked (e.g., tokens)."""
        return Resolver._masked_uri(self.source)

    @property
    def safe_source(self) -> str:
        """
        The source URI as it is safe to send off this machine: without its
        userinfo (``user:token@``), and with every query value masked as ``***``.

        A query's values are where a presigned or tokened URL keeps its
        credential (``?X-Amz-Signature=...``, ``?access_token=...``). Its names
        stay, masked as :attr:`source_print` masks them for a log, so the source
        still says what it is. It no longer says enough to be fetched from.

        It is built from :attr:`source` as written, so an environment variable
        stays a name: its value could be a secret wherever in the URL it lands.
        """
        return Resolver._masked_uri(self.source, show_userinfo=False)

    @property
    def _cache_source(self) -> str:
        """
        The source as :attr:`cache_id` identifies it: expanded, and without its
        userinfo, which says who fetches the data rather than which data it is.

        Unlike :attr:`safe_source` it keeps the query's values, so two sources
        that differ only there keep separate caches.
        """
        url = self.urlparse
        netloc = url.hostname
        if netloc and ":" in netloc:
            netloc = f"[{netloc}]"
        if url.port:
            netloc = f"{netloc}:{url.port}"
        return url._replace(netloc=netloc).geturl()

    @property
    def reference(self) -> Union[None, str]:
        """A version, commit hash, or tag for the source."""
        return self.__reference

    @property
    def urlparse(self) -> "url_parse.ParseResult":
        """The parsed URL of the source after environment variable expansion."""
        from urllib import parse as url_parse

        return url_parse.urlparse(self.__resolve_env(self.source))

    @property
    def urlscheme(self) -> str:
        """The scheme of the source URL (e.g., 'file', 'git')."""
        return self.urlparse.scheme

    @property
    def urlpath(self) -> str:
        """The path component of the source URL."""
        return self.urlparse.netloc

    @property
    def changed(self) -> bool:
        """
        Indicates if the resolved data has changed (e.g., was newly fetched).

        This flag is reset to False after being read.
        """
        change = self.__changed
        self.__changed = False
        return change

    @property
    def cache_id(self) -> str:
        """A unique ID for this resolver instance, used for caching."""
        if self.__cacheid is None:
            # Imported here rather than at module scope: hashlib pulls the
            # _hashlib extension (~1 ms) and only cache-id and digest paths
            # need it.
            import hashlib

            hash_obj = hashlib.sha1()
            hash_obj.update(self._cache_source.encode())
            if self.__reference:
                hash_obj.update(self.__reference.encode())
            else:
                hash_obj.update("".encode())

            self.__cacheid = hash_obj.hexdigest()
        return self.__cacheid

    @property
    def _collection_source(self) -> str:
        """
        The source as :attr:`collection_id` identifies it: as written, without its
        userinfo, which says who fetches the data rather than which data it is, and
        with every query value masked as :attr:`safe_source` masks it.

        The query is masked because a manifest sent off this machine carries the
        source as :attr:`safe_source`, and its reader must name the collection's
        files alike. So two sources that differ only in a query value share a
        collection, as one object presigned twice should.

        It is taken apart as a string, not by ``urllib``, whose parsing has changed
        between Python releases.
        """
        scheme, sep, rest = self.source.partition("://")
        if not sep:
            return self.source
        end = min([rest.find(c) for c in "/?#" if c in rest], default=len(rest))
        tail, hash_sep, fragment = rest[end:].partition("#")
        path, query_sep, query = tail.partition("?")
        if query_sep:
            path = f"{path}?{Resolver._masked_query(query)}"
        return f"{scheme}://{rest[:end].rpartition('@')[2]}{path}{hash_sep}{fragment}"

    @property
    def collection_id(self) -> str:
        """
        An ID for this resolver's data that is the same on every machine, used to
        name its files in a collection.

        A collection is written on one machine and read on another: a remote
        server, a container, wherever an issue testcase is unpacked. :attr:`cache_id`
        identifies where the data is on this machine, so it expands environment
        variables and a relative path, and the reader would compute another. This
        ID is computed only from the source and reference as the manifest records
        them.
        """
        if self.__collectionid is None:
            import hashlib

            payload = json.dumps([self._collection_source, self.__reference or ""],
                                 ensure_ascii=False, separators=(',', ':'))
            self.__collectionid = hashlib.sha1(payload.encode('utf-8')).hexdigest()
        return self.__collectionid

    def set_changed(self):
        """Marks the resolved data as having been changed."""
        self.__changed = True

    def resolve(self) -> Union[Path, str]:
        """
        Abstract method to perform the actual data resolution.

        Subclasses must implement this method to locate or fetch the data
        and return its local path.
        """
        raise NotImplementedError("child class must implement this")

    @property
    def cache(self) -> PathCache:
        """
        :class:`~siliconcompiler.package.cache.PathCache`: The store of paths that
        data sources have resolved to, shared by everything in this process.
        """
        return MPManager.get_path_cache()

    def __abandoned_message(self, cache: PathCache) -> str:
        """Builds the error text used when a data source is given up on."""
        source = self.source_print
        if self.reference:
            source = f"{source} ({self.reference})"
        if cache.is_permanent(self.cache_id):
            # Say why one attempt was enough, so the single try does not read as a
            # retry budget that failed to apply.
            return (f"Unable to resolve '{self.display_name}' from {source}, and "
                    f"retrying cannot change the outcome, giving up. "
                    f"Error: {cache.failure(self.cache_id)}")
        return (f"Unable to resolve '{self.display_name}' from {source} after "
                f"{cache.attempts(self.cache_id)} attempt(s), giving up. "
                f"Last error: {cache.failure(self.cache_id)}")

    def get_path(self) -> str:
        """
        Resolves the data source and returns its local path.

        This method first checks the cache of already resolved paths. If the
        source is not cached, it calls `resolve()` and caches the result.

        Each call makes at most one attempt at resolving the source. For sources
        where an attempt is expensive (see :attr:`is_retryable`), failures are
        counted in the shared :class:`~siliconcompiler.package.cache.PathCache`,
        so the repeated lookups a run performs consume a bounded budget rather
        than re-fetching indefinitely. A failure that a retry could not fix (see
        :meth:`is_permanent_failure`) spends the whole budget at once. Once the
        budget is spent, later calls fail immediately without touching the network.

        Returns:
            str: The absolute path to the resolved data on the local filesystem.

        Raises:
            FileNotFoundError: If the resolved path does not exist.
            DataRootResolutionError: If the source has already failed to resolve
                :attr:`PathCache.max_attempts` times, or has failed permanently.
        """
        cache = self.cache

        if not self.is_indirect:
            cache_path: Optional[str] = cache.get(self.cache_id)
            if cache_path:
                return cache_path

        if self.is_retryable:
            if cache.is_exhausted(self.cache_id):
                raise DataRootResolutionError(self.__abandoned_message(cache))

            # Back off before re-attempting a source that has already failed.
            # Delays live in the cache so resolvers stay a single attempt each
            # and no data source type has to implement its own retry policy.
            cache.wait_before_retry(self.cache_id)

        try:
            path = self.resolve()
            if not os.path.exists(path):
                raise FileNotFoundError(f"Unable to locate '{self.display_name}' at {path}")
        except Exception as e:
            # Deliberately narrower than BaseException: a KeyboardInterrupt or
            # SystemExit says nothing about whether the source is reachable, so
            # it must not consume the budget or poison the cache.
            if self.is_retryable:
                if self.is_permanent_failure(e):
                    cache.record_permanent_failure(self.cache_id, e)
                    self.logger.error(self.__abandoned_message(cache))
                elif cache.record_failure(self.cache_id, e) >= cache.max_attempts:
                    self.logger.error(self.__abandoned_message(cache))
            raise

        if self.is_retryable:
            cache.clear_failure(self.cache_id)

        if self.is_indirect:
            # An indirection owns no location: the resolver it delegated to has
            # already reported where the data is, and its schema-relative source
            # string is not a safe cache key. See :attr:`is_indirect`.
            return str(path)

        if self.changed:
            self.logger.info(f'Saved {self.display_name} data to {path}')
        else:
            self.logger.info(f'Found {self.display_name} data at {path}')

        cache.set(self.cache_id, path)
        return str(path)

    def __resolve_env(self, path: str) -> str:
        """Expands environment variables and user home directory in a path."""
        env_save = os.environ.copy()

        if self.root:
            schema_env = {}
            if self.root.valid("option", "env"):
                for env in self.root.getkeys('option', 'env'):
                    schema_env[env] = self.root.get('option', 'env', env)
            os.environ.update(schema_env)

        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        os.environ.clear()
        os.environ.update(env_save)
        return path


class RemoteResolver(Resolver):
    """
    An abstract base class for resolvers that fetch data from remote sources.

    This class extends `Resolver` with functionality for managing a persistent
    on-disk cache in `~/.sc/cache` or a user-defined location. It implements
    both thread-safe and process-safe locking to prevent race conditions when
    multiple SC instances try to download the same resource simultaneously.
    """

    @property
    def is_retryable(self) -> bool:
        """
        True. Fetching a remote source is expensive, so give up on one that keeps
        failing instead of letting every caller re-download it.
        """
        return True

    def __init__(self, name: str,
                 schema: Optional[Union["Project", "BaseSchema"]],
                 source: str,
                 reference: Optional[str] = None):
        if reference is None:
            raise ValueError(f'A reference (e.g., version, commit) is required for {name}')

        super().__init__(name, schema, source, reference)

        # Wait a maximum of 10 minutes for other processes to finish
        self.__max_lock_wait: int = 60 * 10
        # Give up on a remote server once it has gone a minute without answering
        self.__request_timeout: int = 60

    @property
    def lock_timeout(self) -> int:
        """The maximum time in seconds to wait for a lock."""
        return self.__max_lock_wait

    def set_lock_timeout(self, value: int) -> None:
        """Sets the maximum time in seconds to wait for a lock."""
        self.__max_lock_wait = value

    @property
    def request_timeout(self) -> int:
        """
        The maximum time in seconds a request to a remote server may wait to
        connect, or between one part of the answer and the next.

        It bounds a stall, not a transfer: a large download that keeps arriving
        takes as long as it takes. A request that times out is retried, as a
        dropped connection is.
        """
        return self.__request_timeout

    def set_request_timeout(self, value: int) -> None:
        """Sets the maximum time in seconds a request to a remote server may
        stall (see :attr:`request_timeout`)."""
        self.__request_timeout = value

    @property
    def cache_dir(self) -> Path:
        """The directory for the on-disk cache."""
        return Path(datarootdir(self.root))

    @property
    def cache_name(self) -> str:
        """A unique name for the cached data directory."""
        return f"{self.name}-{self.reference[0:16]}-{self.cache_id[0:16]}"

    @property
    def cache_path(self) -> Path:
        """The full path to the cached data directory."""
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        return self.cache_dir / self.cache_name

    @property
    def lock_file(self) -> Path:
        """The path to the file used for inter-process locking."""
        return Path(get_file_lock(self.cache_path).lock_path)

    @property
    def sc_lock_file(self) -> Path:
        """
        The path to a secondary lock file used as a fallback mechanism.

        Where the filesystem cannot lock :attr:`lock_file`, the lock is held by
        creating this file instead (see
        :attr:`~siliconcompiler.utils.multiprocessing.FileLock.fallback_path`).
        """
        return Path(get_file_lock(self.cache_path).fallback_path)

    def thread_lock(self) -> threading.Lock:
        """
        Gets the download lock for this resolver's data source.

        The lock is keyed by :attr:`cache_id`, so resolvers for unrelated sources
        never contend. Note this is not the same granularity as
        :attr:`lock_file`, which is derived from :attr:`cache_name` and so also
        varies with :attr:`name`: two resolvers naming one source differently
        share this lock but take different lock files, because they also download
        to different :attr:`cache_path` directories.
        """
        return self.cache.thread_lock(self.cache_id)

    @contextlib.contextmanager
    def __thread_lock(self):
        """A context manager for acquiring the thread lock with a timeout."""
        lock = self.thread_lock()
        lock_acquired = False
        try:
            timeout = self.lock_timeout
            while timeout > 0:
                if lock.acquire_lock(timeout=1):
                    lock_acquired = True
                    break
                sleep_time = random.randint(1, max(1, int(timeout / 10)))
                timeout -= sleep_time + 1
                time.sleep(sleep_time)
            if lock_acquired:
                yield
        finally:
            # Only release a lock this context actually took. threading.Lock has
            # no notion of an owner, so releasing on the strength of locked()
            # would let a waiter that timed out free the holder's lock and admit
            # a third thread into the download.
            if lock_acquired:
                lock.release()

        if not lock_acquired:
            raise RuntimeError(f'Failed to access {self.cache_path}. '
                               f'Another thread is currently holding the lock.')

    @contextlib.contextmanager
    def __file_lock(self):
        """
        A context manager for acquiring the inter-process file lock.

        The process's shared lock on :attr:`lock_file` (see
        :func:`~siliconcompiler.utils.multiprocessing.get_file_lock`), so the
        cache sweep in another thread sees a download in progress. Where the
        filesystem cannot lock files, it is held as :attr:`sc_lock_file`
        instead.
        """
        lock = get_file_lock(self.cache_path)
        try:
            lock.acquire(self.lock_timeout)
        except FileLockTimeout as e:
            if e.fallback:
                raise RuntimeError(f'Failed to access {self.cache_path}. '
                                   f'Lock {e.fallback} still exists.') from None
            raise RuntimeError(f'Failed to access {self.cache_path}. '
                               f'{self.lock_file} is still locked. If this is a mistake, '
                               'please delete the lock file.') from None
        try:
            yield
        finally:
            lock.release()

    @contextlib.contextmanager
    def lock(self):
        """
        A context manager that acquires both the thread and file locks.

        This ensures that only one thread in one process can access the cache
        for a specific resource at a time.
        """
        with self.__thread_lock():
            with self.__file_lock():
                yield

    def resolve_remote(self) -> None:
        """Abstract method to fetch the remote data."""
        raise NotImplementedError("child class must implement this")

    def check_cache(self) -> bool:
        """
        Abstract method to check if the on-disk cache is valid.

        Returns:
            bool: True if the cache is valid, False otherwise.
        """
        raise NotImplementedError("child class must implement this")

    def resolve(self) -> Union[str, Path]:
        """
        Resolves the remote data, using the on-disk cache if possible.

        This method acquires locks, checks the cache validity, and calls
        `resolve_remote()` to fetch the data if the cache is missing or invalid.

        Returns:
            Path: The path to the locally cached data.
        """
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except OSError:
                # Can't create directory, return path and let it fail later
                return self.cache_path

        if not os.access(self.cache_dir, os.W_OK):
            # Can't write to directory, assume cache is valid if it exists
            return self.cache_path

        with self.lock():
            if self.check_cache():
                self._touch_lock()
                return self.cache_path

            try:
                self.resolve_remote()
            except BaseException:
                # Exception occurred, so need to cleanup
                try:
                    # Make writable first, in case cache was partially made read-only
                    try:
                        self._make_writable(self.cache_path)
                    except OSError as e:
                        self.logger.warning(f"Could not make cache writable before cleanup: {e}")
                    try:
                        shutil.rmtree(self.cache_path)
                    except FileNotFoundError:
                        # git removes a failed clone's directory itself, so a
                        # missing path is the normal case and must not be logged
                        # over the failure that brought us here. Anything else
                        # still reaches the handler below: a cache this could not
                        # remove is one a later run may wrongly accept.
                        pass
                except BaseException as cleane:
                    self.logger.error(f"Exception occurred during cleanup: {cleane} "
                                      f"({cleane.__class__.__name__})")
                raise

            # Make all cached files read-only to prevent accidental modifications
            try:
                self._make_readonly(self.cache_path)
            except OSError as e:
                self.logger.warning(f"Could not make cache read-only: {e}")

            self._touch_lock()
            self.set_changed()
            return self.cache_path

    def _touch_lock(self) -> None:
        """
        Records now as the time this cache entry was last accessed.

        Nothing else in the cache carries that information: a hit returns the
        path and reads nothing, and the cached tree is made read-only after the
        download, so every mtime inside it stays frozen at the fetch. The lock
        file is the one writable thing beside an entry, which is why
        :mod:`siliconcompiler.package.cleanup` reads its mtime as the access
        time -- and it only means that because a resolve stamps it here.

        Called with the entry's lock held, so no other process is mid-download.
        Failure is not worth interrupting a resolve over; it only costs the
        entry its place in the access record.
        """
        try:
            self.lock_file.touch()
        except OSError as e:
            self.logger.debug(f"Could not update access time of {self.lock_file}: {e}")

    @staticmethod
    def _make_readonly(path: Union[str, Path]) -> None:
        """
        Recursively makes all files and directories in the given path read-only.

        This prevents accidental modification of cached remote data by removing write
        permissions while preserving executable bits and read access. Note: git does
        not track full file permissions (only the executable bit), so this operation
        will not create a dirty warning in git repositories.

        Any directory named ``.git`` is skipped so git's internal state (including
        ``.git/lfs/tmp`` and per-submodule ``.git/modules/<name>``) stays writable —
        otherwise routine git operations like diff/status fail on LFS-tracked repos
        because the clean filter cannot buffer through ``.git/lfs/tmp``.

        Args:
            path: The path to make read-only (file or directory).
        """
        path = Path(path)
        # Skip symlinks to avoid following them outside the cache
        if path.is_symlink():
            return
        # Preserve writability of git's internal state directories
        if path.is_dir() and path.name == ".git":
            return
        if path.is_file():
            # Remove write permissions, preserve everything else (especially execute bit)
            current_mode = os.stat(path).st_mode
            new_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            os.chmod(path, new_mode)
        elif path.is_dir():
            # Process all contents recursively
            for item in path.iterdir():
                RemoteResolver._make_readonly(item)
            # Remove write permissions from the directory itself
            current_mode = os.stat(path).st_mode
            new_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            os.chmod(path, new_mode)

    @staticmethod
    def _make_writable(path: Union[str, Path]) -> None:
        """
        Recursively makes all files and directories in the given path writable.

        This is used before deletion to ensure that read-only cached files can be
        properly removed when necessary (e.g., for corrupted cache cleanup).

        Args:
            path: The path to make writable (file or directory).
        """
        path = Path(path)
        # Skip symlinks to avoid following them outside the cache
        if path.is_symlink():
            return
        if path.is_file():
            # Add owner write permission, preserve everything else
            current_mode = os.stat(path).st_mode
            new_mode = current_mode | stat.S_IWUSR
            os.chmod(path, new_mode)
        elif path.is_dir():
            # Process all contents recursively
            for item in path.iterdir():
                RemoteResolver._make_writable(item)
            # Add owner write permission to the directory itself
            current_mode = os.stat(path).st_mode
            new_mode = current_mode | stat.S_IWUSR
            os.chmod(path, new_mode)

    @staticmethod
    def _host_forge(hostname: Optional[str]) -> Optional[str]:
        """
        Identifies which forge a hostname belongs to.

        Matches whole dot-separated labels, so a self-hosted instance
        (``gitlab.example.com``, ``github.mycorp.com``) is recognised while an
        unrelated host that merely contains the name (``mygithub.internal``) is
        not. Not an ownership check: see :meth:`_saas_forge` for that.

        Args:
            hostname (str or None): The host from the source URL.

        Returns:
            str or None: The forge key, or None if the host is unrecognised.
        """
        if not hostname:
            return None
        labels = hostname.lower().split('.')
        for forge in ("github", "gitlab", "bitbucket"):
            if forge in labels:
                return forge
        return None

    @staticmethod
    def _saas_forge(hostname: Optional[str]) -> Optional[str]:
        """
        Identifies a forge's own hosted service, by exact domain.

        This is the ownership check that decides whether a forge's own variables
        -- ``GITHUB_TOKEN`` and the rest, set ambiently on CI runners and
        developer machines -- may be sent to a host. It is deliberately stricter
        than :meth:`_host_forge`. Matching a forge name in any label is fine for
        choosing a username, or how to unpack an archive -- neither is a secret
        -- but it is not evidence of who owns a host, and
        ``gitlab.attacker.example`` must not be handed the ambient
        ``GITLAB_TOKEN``. A self-hosted instance supplies its credential through
        a generic variable, or through a username in the URL.

        Args:
            hostname (str or None): The host from the source URL.

        Returns:
            str or None: The forge key, or None if the host is not that forge's.
        """
        if not hostname:
            return None
        host = hostname.lower()
        for forge, domain in (("github", "github.com"),
                              ("gitlab", "gitlab.com"),
                              ("bitbucket", "bitbucket.org")):
            if host == domain or host.endswith(f".{domain}"):
                return forge
        return None

    def _get_auth_token(self, prefix: List[str]) -> str:
        """
        Retrieves an authentication token from environment variables.

        Args:
            prefix (List[str]): A list of prefixes to search for in environment variable names.
                For example, if prefix is ['GITHUB'], it will look for 'GITHUB_<PACKAGE_NAME>_TOKEN'
                and 'GITHUB_TOKEN'.

        Returns:
            str: The found token.

        Raises:
            ValueError: If no token can be found in the environment, or a
                :class:`FetchPolicy` is active: under one nothing is sent.
        """
        if current_fetch_policy() is not None:
            raise ValueError("no credential is sent under a fetch policy")

        token_name = self.name.upper()
        # Sanitize package name for environment variable compatibility
        for char in ('#', '$', '&', '-', '=', '!', '/', '.'):
            token_name = token_name.replace(char, '')

        search_env = []
        for prf in prefix:
            search_env.append(f"{prf.upper()}_{token_name}_TOKEN")
            search_env.append(f"{prf.upper()}_TOKEN")

        for env in search_env:
            token = os.environ.get(env)
            if token:
                return token

        raise ValueError('Unable to determine authorization token. Please set one of the '
                         f'following environment variables: {", ".join(search_env)}')


class FileResolver(Resolver):
    """
    A resolver for local file system paths.

    It handles both absolute paths and paths relative to the project's CWD.
    It normalizes the source string to a `file://` URI.
    """

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        is_private = False
        if source.startswith("file://"):
            source = source[7:]
        elif source.startswith("file+private://"):
            is_private = True
            source = source[15:]
        self.__recorded = source
        if source[0] != "$" and not os.path.isabs(source):
            source = os.path.join(cwdirsafe(schema._parent(root=True)), source)

        super().__init__(name, schema, f"file{'+private' if is_private else ''}://{source}", None)

    @property
    def urlpath(self) -> str:
        """The absolute file path, stripped of the 'file://' prefix."""
        # Rebuild URL and remove scheme prefix
        return self.urlparse.geturl()[7:]

    @property
    def safe_source(self) -> str:
        # A path has no userinfo or query: an '@' or a '?' in it is part of a
        # name, and a Windows drive would read as a host.
        return self.source

    @property
    def _cache_source(self) -> str:
        return self.urlparse.geturl()

    @property
    def _collection_source(self) -> str:
        # As recorded: a relative path is not joined to this machine's cwd
        return f"file://{self.__recorded}"

    def resolve(self) -> str:
        """Returns the absolute path to the file."""
        path = self.urlpath
        if path and path[0] == "$":
            return path
        return os.path.abspath(path)


class PythonPathResolver(Resolver):
    """
    A resolver for locating installed Python packages.

    This resolver uses Python's import machinery to find the installation
    directory of a given Python module, as in ``python://siliconcompiler``, or
    of a directory inside it, as in ``python://siliconcompiler/tools/openroad``.
    It also includes helper methods to determine if a package is installed in
    "editable" mode.
    """

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, schema, source, None)

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_python_module_mapping() -> Dict[str, List[str]]:
        """
        Creates a mapping from importable module names to their distribution names.

        This is used to find the distribution package that provides a given module.

        Returns:
            dict: A dictionary mapping module names to a list of distribution names.
        """
        # Imported here rather than at module scope: importlib.metadata costs a
        # couple of ms and only the python-module resolver needs it.
        from importlib.metadata import distributions

        mapping = {}

        for dist in distributions():
            dist_name = getattr(dist, 'name', None)
            if not dist_name:
                metadata = dist.read_text('METADATA')
                if metadata:
                    find_name = re.compile(r'Name: (.*)')
                    for data in metadata.splitlines():
                        group = find_name.findall(data)
                        if group:
                            dist_name = group[0]
                            break

            if not dist_name:
                continue

            provides = dist.read_text('top_level.txt')
            if provides:
                for module in provides.split():
                    mapping.setdefault(module, []).append(dist_name)

        return mapping

    @staticmethod
    def is_python_module_editable(module_name: str) -> bool:
        """
        Checks if a Python module is installed in "editable" mode.

        Args:
            module_name (str): The name of the Python module to check.

        Returns:
            bool: True if the module is installed in editable mode, False otherwise.
        """
        dist_map = PythonPathResolver.get_python_module_mapping()
        if module_name not in dist_map:
            return False
        dist_name = dist_map[module_name][0]

        from importlib.metadata import distribution

        dist_obj = distribution(dist_name)
        if not dist_obj:
            return False

        direct_url_content = dist_obj.read_text('direct_url.json')
        if direct_url_content:
            direct_url = json.loads(direct_url_content)
            return direct_url.get('dir_info', {}).get('editable', False)

        dist_loc = dist_obj.locate_file('')
        site_paths = site.getsitepackages()
        user_site_path = site.getusersitepackages()
        if user_site_path:
            site_paths.append(user_site_path)
        if not dist_loc or not site_paths:
            return False

        dist_loc = PureWindowsPath(dist_loc).as_posix()
        return dist_loc not in [PureWindowsPath(site_path).as_posix() for site_path in site_paths]

    @staticmethod
    def set_dataroot(root: "PathSchema",
                     package_name: str,
                     python_module: str,
                     alternative_path: str,
                     alternative_ref: Optional[str] = None,
                     python_module_path_append: Optional[str] = None):
        """
        Helper to conditionally set a dataroot to a Python module or a fallback path.
        """
        # check if installed in an editable state
        if PythonPathResolver.is_python_module_editable(python_module):
            path = f"python://{python_module}"
            if python_module_path_append:
                py_path = PythonPathResolver(python_module, root, path).resolve()
                path = os.path.abspath(os.path.join(py_path, python_module_path_append))
            ref = None
        else:
            path = alternative_path
            ref = alternative_ref

        root.set_dataroot(package_name, path=path, tag=ref)

    def resolve(self) -> str:
        """
        Resolves the path to the specified Python module, or to a directory
        inside it when the source names one, as in
        ``python://siliconcompiler/tools/openroad``.

        Returns:
            str: The absolute path to the module's directory, or to the
            directory named inside it.
        """
        module = importlib.import_module(self.urlpath)
        python_path = os.path.dirname(module.__file__)
        # A path, not a submodule: it is not imported, and need not be a package
        return os.path.abspath(os.path.join(python_path, self.urlparse.path.lstrip("/")))


class KeyPathResolver(Resolver):
    """
    A resolver for finding file paths stored within the project schema itself.

    This resolver takes a keypath (e.g., 'tool,openroad,exe') and uses the
    `find_files` method of the root project object to locate the corresponding file.
    """

    @property
    def is_indirect(self) -> bool:
        """True. A keypath names something inside a schema, not a location."""
        return True

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, schema, source, None)

    def resolve(self) -> str:
        """
        Resolves the path by looking up the keypath in the project schema.

        Returns:
            str: The file path found in the schema.

        Raises:
            RuntimeError: If the resolver does not have a root project object defined.
        """
        if not self.root:
            raise RuntimeError(f"A root schema has not been defined for '{self.display_name}'")

        key = self.urlpath.split(",")
        if self.root.get(*key, field='pernode').is_never():
            paths = self.root.find_files(*key)
        else:
            paths = self.root.find_files(*key,
                                         step=self.root.get('arg', 'step'),
                                         index=self.root.get('arg', 'index'))

        if isinstance(paths, list):
            return paths[0]
        return paths


class DatarootResolver(Resolver):
    """
    A resolver for finding file paths stored with other dataroots.
    """

    @property
    def is_indirect(self) -> bool:
        """
        True. A dataroot name is only meaningful within the schema that defines
        it, and the dataroot it points at is resolved by its own resolver.
        """
        return True

    def __init__(self, name: str, schema: "Project", source: str, reference: Optional[str] = None):
        super().__init__(name, schema, source, None)
        # Track visited dataroots passed from parent resolver for cycle detection
        self._parent_visited: Optional[set] = None

    def __target(self) -> Resolver:
        """
        The resolver for the dataroot this one names.

        Raises:
            RuntimeError: If the resolver does not have a schema context, if the
                dataroot is not defined in the registry, or if a circular
                dataroot reference is detected during resolution.
        """
        if not self.schema:
            raise RuntimeError(f"A schema context is required for '{self.display_name}'")

        # The registry the dataroot naming this one came from, wherever its
        # schema sits: a design inside a project as well as on its own
        datarootstore = self.schema._dataroot_section()

        find_root = self.urlpath
        if not datarootstore.valid('dataroot', self.urlpath):
            raise RuntimeError(
                f"Dataroot '{self.urlpath}' is not defined for '{self.display_name}'")

        # Use visited set from parent, or start new one if this is top-level
        visited = self._parent_visited if self._parent_visited is not None else set()

        # Check for circular dataroot references
        if find_root in visited:
            raise RuntimeError(
                f"Circular dataroot reference detected: '{find_root}' is part of a reference cycle")

        # Mark this dataroot as visited
        visited_copy = visited.copy()
        visited_copy.add(find_root)

        path: str = datarootstore.get("dataroot", find_root, "path")
        tag: Optional[str] = datarootstore.get("dataroot", find_root, "tag")

        resolver = Resolver.find_resolver(path)
        resolver_instance = resolver(self.name, self.schema, path, tag)

        # If the next resolver is also a DatarootResolver, pass the visited set to it
        if isinstance(resolver_instance, DatarootResolver):
            resolver_instance._parent_visited = visited_copy

        return resolver_instance

    @property
    def _collection_source(self) -> str:
        # The name means another dataroot in every schema, so the dataroot it
        # names identifies it
        subpath = self.source.partition("://")[2].partition("/")[2]
        return f"dataroot://{self.__target().collection_id}/{subpath}"

    def resolve(self) -> str:
        """
        Resolves a dataroot by looking up its configured path and resolving it.

        This resolver looks up a dataroot by name in the dataroot registry, retrieves
        its configured path (which may be a file://, python://, or another dataroot://),
        and resolves that path using the appropriate resolver. This allows dataroots
        to reference other dataroots, forming resolution chains.

        Returns:
            str: The resolved absolute path for the dataroot.

        Raises:
            RuntimeError: If the resolver does not have a schema context, if the
                dataroot is not defined in the registry, or if a circular
                dataroot reference is detected during resolution.
        """
        base_path = self.__target().get_path()
        # Strip leading '/' from urlparse.path to avoid os.path.join treating it as absolute
        subpath = self.urlparse.path.lstrip('/')
        return os.path.join(base_path, subpath) if subpath else base_path
