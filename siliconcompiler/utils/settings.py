import contextlib
import json
import os
import logging
import secrets
import stat
import threading
import time
import weakref

import os.path

from typing import Generator, Optional, Tuple

from siliconcompiler import sc_open
from siliconcompiler.utils.multiprocessing import FileLockTimeout, get_file_lock


#: Every live SettingsManager, so a forked child can rebuild their locks.
_managers: "weakref.WeakSet[SettingsManager]" = weakref.WeakSet()

#: How long a save keeps retrying a replace that Windows refuses while another
#: program -- an editor, a virus scanner, the search indexer -- has the file
#: open. POSIX never refuses, so it never waits.
_REPLACE_RETRY: float = 1.0 if os.name == "nt" else 0.0

#: Without it, Windows opens a descriptor in text mode and translates newlines
#: a second time underneath the text wrapper.
_O_BINARY: int = getattr(os, "O_BINARY", 0)


def _make_directory(directory: str, mode: Optional[int]) -> None:
    """
    Create ``directory`` if it is missing.

    With ``mode``, the directory is created with it, plus search permission
    wherever it grants read: ``0o600`` makes a ``0o700`` directory. As with
    :func:`os.makedirs`, only the last component gets the mode.
    """
    if not directory or os.path.isdir(directory):
        return
    if mode is None:
        os.makedirs(directory, exist_ok=True)
    else:
        os.makedirs(directory, mode=mode | ((mode & 0o444) >> 2), exist_ok=True)


def _create_file(path: str, mode: int) -> None:
    """
    Create ``path`` empty with ``mode``, and its directory, if it does not exist.
    """
    _make_directory(os.path.dirname(path), mode)
    if not os.path.exists(path):
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | _O_BINARY, mode))


def _create_temp(target: str, mode: int) -> Tuple[int, str]:
    """
    Create a new, empty file beside ``target`` with ``mode``.

    Not :func:`tempfile.mkstemp`, which always creates ``0600``. Named after the
    target, and hidden, so one a crash left behind says what it was.

    Returns:
        tuple: the open descriptor and the file's path.
    """
    directory, name = os.path.split(target)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_BINARY
    for _ in range(100):
        path = os.path.join(directory, f".{name}.{secrets.token_hex(4)}.tmp")
        try:
            return os.open(path, flags, mode), path
        except FileExistsError:
            continue
    raise FileExistsError(f"No free temporary file name beside {target}")


def _replace(source: str, target: str) -> None:
    """
    :func:`os.replace`, retried for up to :data:`_REPLACE_RETRY` seconds while
    the target is refused.
    """
    deadline = time.monotonic() + _REPLACE_RETRY
    while True:
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


def _reset_locks_after_fork() -> None:
    """
    Rebuilds every manager's locks in a freshly forked child.

    A child inherits each lock in the state it had at the instant of the fork,
    and a lock held by a thread that does not exist in the child is never
    released. SiliconCompiler forks its scheduler workers (see
    :func:`~siliconcompiler.utils.multiprocessing.get_process_context`) out of a
    process that may well have another thread inside
    :meth:`SettingsManager.lock_category` at the time.

    Discarding the locks is safe precisely because the child has one thread: no
    update can be in progress in it. What the child *may* have inherited is a
    category left half-written by the parent, which is why a category built in
    steps needs a completion marker rather than a lock alone -- see
    :meth:`SettingsManager.lock_category`.

    The file locks are reset by
    :func:`~siliconcompiler.utils.multiprocessing.get_file_lock`'s own hook, so
    a transaction does not carry into the child: one forked from inside a
    transaction holds nothing there.
    """
    for manager in list(_managers):
        manager._reset_locks()


if hasattr(os, "register_at_fork"):  # absent on Windows, which has no fork
    os.register_at_fork(after_in_child=_reset_locks_after_fork)


class SettingsManager:
    """
    A class to manage user settings stored in a JSON file.
    Supports categories, robust error handling for malformed files,
    and simple get/set operations.

    An optional read-only, administrator-managed *system* settings file can be
    layered underneath the user file. System settings act as defaults that the
    user may override, except for values the system marks with *system
    priority*, which take precedence over the user's own value. This provides
    both soft defaults and administrator-enforced values from a single file
    (see ``system_filepath``).

    In the system file, a value is given system priority by co-locating a flag
    with it. Instead of a bare value, the setting is written as an object with a
    ``"system_priority"`` flag (and, optionally, a ``"value"``)::

        {
            "record": {
                "region": {"value": "us-east-1", "system_priority": true}
            },
            "scheduler-slurm": {
                "sharedpaths": ["/nfs/tools"]
            }
        }

    Here ``region`` is a system-priority value that the user cannot override
    while ``sharedpaths`` is a plain, overridable default. The priority flag is
    only interpreted in the system file; a value written this way in a user file
    is treated as an ordinary (dictionary) value, so existing user files are
    unaffected.
    """

    #: Key that marks a system value as taking priority over the user value.
    __PRIORITY_FLAG = "system_priority"
    #: Key that carries the actual value alongside a priority flag.
    __VALUE_FLAG = "value"

    def __init__(self, filepath: str, logger: logging.Logger, timeout: float = 1.0,
                 system_filepath: Optional[str] = None, mode: Optional[int] = None):
        """
        Initialize the settings manager.

        Args:
            filepath (str): The path to the JSON file where user settings are
                stored. If None, settings are kept in memory only.
            logger (logging.Logger): Logger for logging errors and information.
            timeout (float): Timeout in seconds for acquiring the file lock.
            system_filepath (str): Optional path to a read-only, system-wide
                settings file providing administrator-managed defaults and
                system-priority (non-overridable) values. If None, no system
                layer is applied.
            mode (int): Optional POSIX permission bits, such as ``0o600``, that
                the settings file, its temporary files and its lock file are
                each created with -- never changed afterwards, so the file is
                never readable more widely, even for a moment. A directory the
                manager creates for them gets the same bits plus search
                permission. The umask still applies. If None, the file keeps
                the permissions it has, and a new one gets the umask's.
                Ignored on Windows.
        """
        self.__filepath = filepath
        self.__mode = mode if os.name != "nt" else None
        # Three levels of lock, always taken in this order:
        #   1. the file's lock (see multiprocessing.FileLock), shared by
        #      everything in the process that locks the file, and taken here
        #      only by _load, save and transaction;
        #   2. a category lock, held for as long as a caller is building that
        #      category (see lock_category) and taken by every accessor;
        #   3. __settings_lock, held only for the dict operations themselves.
        # A transaction holds 1 while its body takes 2 and 3, which is why
        # nothing may save or open a transaction while holding 2 or 3.
        self.__settings_lock = threading.Lock()
        self.__category_locks = {}
        self.__category_locks_lock = threading.Lock()
        # A file-less manager's stand-in for 1, so its transactions still
        # exclude one another.
        self.__memory_lock = threading.RLock()
        # Per thread, how deep in this manager's transactions it is.
        self.__transactions = threading.local()
        _managers.add(self)
        self.__timeout = timeout
        self.__logger = logger.getChild("settings")
        self.__settings = {}
        # Why the last load left nothing safe to save, if it did.
        self.__load_error: Optional[str] = None

        # System layer state: resolved (unwrapped) values plus the set of
        # system-priority keys per category.
        self.__system_filepath = system_filepath
        self.__system_settings = {}
        self.__priority = {}

        self._load()
        self._load_system()

    def _load(self):
        """
        Internal method to load settings from disk.

        Never raises: a file that is missing, malformed or cannot be read is
        logged and loads as empty. Where it could not be read at all -- the lock
        was not had in time, or an unexpected error -- :meth:`save` refuses
        afterwards, since the empty copy would replace whatever the file holds.
        A malformed file is already lost, and saving over it is how it is
        repaired.
        """
        self.__load_error = None
        if self.__filepath is None or not os.path.exists(self.__filepath):
            with self.__settings_lock:
                self.__settings = {}
            return

        try:
            with self._locked():
                data = self._read()
        except FileLockTimeout:
            self.__logger.error(f"Timeout acquiring lock for {self.__filepath}. "
                                "Starting with empty settings.")
            self.__load_error = "its lock was not had in time"
            data = {}
        except json.JSONDecodeError:
            self.__logger.error(f"File {self.__filepath} is malformed. "
                                "Starting with empty settings.")
            data = {}
        except Exception as e:
            # Catch-all for permission errors, etc., to ensure __init__ doesn't crash
            self.__logger.error(f"Unexpected error loading settings: {e}")
            self.__load_error = f"it could not be read: {e}"
            data = {}

        # Ensure the loaded data is actually a dictionary
        if not isinstance(data, dict):
            # If valid JSON but not a dict (e.g. a list), reset to empty
            self.__logger.warning(f"File {self.__filepath} did not contain a JSON object. "
                                  "Resetting.")
            data = {}

        with self.__settings_lock:
            self.__settings = data

    def _read(self):
        """
        Read the user file, whose lock the caller holds.

        Returns:
            The parsed JSON, which may not be a dict, or an empty dict where
            there is no file.

        Raises:
            json.JSONDecodeError: if the file does not parse.
        """
        if not os.path.exists(self.__filepath):
            return {}
        with sc_open(self.__filepath, encoding='utf-8') as f:
            return json.load(f)

    @contextlib.contextmanager
    def _locked(self, timeout: Optional[float] = None) -> Generator[None, None, None]:
        """
        Hold the user file's lock.

        Args:
            timeout (float): Seconds to wait for it; the manager's own timeout
                where None.

        Raises:
            TimeoutError: if the lock is not had in time.
        """
        if timeout is None:
            timeout = self.__timeout
        # Looked up on every use rather than kept: tests point a live manager
        # at another file by replacing its filepath.
        lock = get_file_lock(self.__filepath)
        if self.__mode is not None:
            # Before the lock opens it, which would create it at the umask.
            _create_file(lock.lock_path, self.__mode)
        with lock.locked(timeout):
            yield

    def _load_system(self):
        """
        Internal method to load the read-only system settings file, if any.

        Unlike the user file, the system file is never locked (it is
        administrator-managed and typically lives in a location such as
        ``/etc`` where regular users cannot create the sibling lock file) and is
        never written to. Any failure to read it is logged and treated as if no
        system file were present, so it can never prevent startup.

        Inline priority flags are unwrapped here into ``__system_settings``
        (bare values) and ``__priority`` (the set of system-priority keys per
        category).
        """
        self.__system_settings = {}
        self.__priority = {}

        if self.__system_filepath is None or not os.path.exists(self.__system_filepath):
            return

        try:
            with sc_open(self.__system_filepath, encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            self.__logger.error(f"System settings file {self.__system_filepath} is malformed. "
                                "Ignoring system settings.")
            return
        except Exception as e:
            self.__logger.error(f"Unexpected error loading system settings: {e}")
            return

        if not isinstance(data, dict):
            self.__logger.warning(f"System settings file {self.__system_filepath} did not contain "
                                  "a JSON object. Ignoring system settings.")
            return

        self._unwrap_system(data)

    def _is_priority_wrapper(self, value) -> bool:
        """
        Return True if a raw system value is a co-located priority wrapper, i.e.
        a JSON object carrying a ``system_priority`` flag.
        """
        return isinstance(value, dict) and self.__PRIORITY_FLAG in value

    def _unwrap_system(self, data: dict):
        """
        Split raw system data into resolved values and system-priority keys.

        Each setting is either a bare value (a plain, overridable default) or a
        priority wrapper (an object with a ``system_priority`` flag and optional
        ``value``). System-priority keys are recorded per category; a wrapper
        without a ``value`` gives priority to "unset", forcing callers to fall
        back to their default.
        """
        for category, entries in data.items():
            if not isinstance(entries, dict):
                self.__logger.warning(f"System settings category '{category}' is not a JSON "
                                      "object. Ignoring.")
                continue

            values = {}
            priority = set()
            for key, raw in entries.items():
                if self._is_priority_wrapper(raw):
                    if raw.get(self.__PRIORITY_FLAG):
                        priority.add(key)
                    if self.__VALUE_FLAG in raw:
                        values[key] = raw[self.__VALUE_FLAG]
                else:
                    values[key] = raw

            self.__system_settings[category] = values
            if priority:
                self.__priority[category] = priority

    def _has_priority(self, category: str, key: str) -> bool:
        """
        Return True if the given category/key is a system-priority value and
        therefore not user-overridable.
        """
        return key in self.__priority.get(category, ())

    def _reset_locks(self) -> None:
        """
        Replaces every lock with a fresh one. See :func:`_reset_locks_after_fork`.
        """
        self.__settings_lock = threading.Lock()
        self.__category_locks = {}
        self.__category_locks_lock = threading.Lock()
        self.__memory_lock = threading.RLock()

    def _category_lock(self, category: str) -> threading.RLock:
        """
        Return the lock guarding one category, creating it on first use.

        Re-entrant by design: every accessor takes this lock, so the thread
        holding a category open under :meth:`lock_category` has to be able to
        take it again to do the work it opened the category for.
        """
        with self.__category_locks_lock:
            if category not in self.__category_locks:
                self.__category_locks[category] = threading.RLock()
            return self.__category_locks[category]

    @contextlib.contextmanager
    def lock_category(self, category: str) -> Generator[None, None, None]:
        """
        Hold a category for the length of a multi-step update.

        A category assembled one :meth:`set` at a time is readable while it is
        still being assembled: another thread sees the keys written so far and
        has nothing to tell it the rest is still coming. Hold the category while
        writing it and every other thread's access to *that* category waits for
        the release. Other categories are unaffected, and the holder's own
        :meth:`get`, :meth:`set` and :meth:`delete` calls run normally -- the
        lock excludes other threads, not the one doing the work.

        Note this is a lock, not a completion record, and the two are not the
        same thing across a ``fork``: a child forked mid-update inherits the
        half-written category with nothing held (see
        :func:`_reset_locks_after_fork`). A category built in steps should
        therefore still write a marker key last and test *that*, rather than
        reading "the category is non-empty" as "the category is finished".

        Do not :meth:`save` or open a :meth:`transaction` while holding a
        category. A transaction holds the file's lock while its body takes
        category locks, so taking them the other way round deadlocks against
        one.

        Args:
            category (str): The group name to hold.
        """
        with self._category_lock(category):
            yield

    def save(self):
        """
        Save the current settings to the disk in JSON format.

        The file is replaced, never rewritten in place: the settings are written
        to a temporary file beside it, flushed to disk and renamed over it, so a
        crash or an error at any point leaves either the previous file or the
        new one, whole. A symlinked file is followed, and its target replaced.

        This writes the whole in-memory copy: what was loaded when the manager
        was built, plus every change since. Where another process may have
        changed the file in the meantime, make the change in a
        :meth:`transaction` instead, which re-reads it first.

        Raises:
            TimeoutError: if the file's lock is not had within the manager's
                timeout. Nothing is written.
            RuntimeError: if the file could not be loaded when the manager was
                built, so saving would replace what it holds with only the
                changes made since. A :meth:`transaction` re-reads it and
                lifts this.
        """
        if self.__filepath is None:
            return

        try:
            if self.__load_error is not None:
                raise RuntimeError(f"{self.__filepath} was not loaded ({self.__load_error}), "
                                   "so saving would replace what it holds")
            with self._locked():
                self._write(self._serialize())
        except Exception as e:
            self.__logger.error(f"Failed to save settings to {self.__filepath}: {e}")
            raise

    def _serialize(self) -> str:
        """
        The user settings as they are written to the file.
        """
        with self.__settings_lock:
            return json.dumps(self.__settings, indent=4)

    def _write(self, content: str) -> None:
        """
        Replace the user file with ``content``; the caller holds its lock.
        """
        target = os.path.realpath(self.__filepath)
        _make_directory(os.path.dirname(target), self.__mode)

        mode = self.__mode
        if mode is None:
            # What open("w") would have kept, or given a new file.
            try:
                mode = stat.S_IMODE(os.stat(target).st_mode) & 0o777
            except FileNotFoundError:
                mode = 0o666

        fd, temp = _create_temp(target, mode)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            _replace(temp, target)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temp)
            raise

    @contextlib.contextmanager
    def transaction(self, timeout: Optional[float] = None) -> Generator[None, None, None]:
        """
        Change the settings file as one step, with every other writer kept out.

        Takes the file's lock, re-reads the file, runs the block, and saves on a
        clean exit if the block changed anything. Another process, another
        thread, or another manager on the same file waits for the lock rather
        than writing in between, so what it wrote before is kept rather than
        overwritten from a stale copy::

            with settings.transaction():
                settings.set("category", "key", value)

        Inside the block, :meth:`get`, :meth:`set`, :meth:`delete` and
        :meth:`get_category` work as usual. On an exception nothing is saved,
        and the in-memory settings go back to what the file held. A transaction
        nested in another on the same manager joins it: only the outermost
        re-reads and saves.

        Changes made before the transaction and not yet saved are discarded, in
        every thread: the re-read replaces the whole in-memory copy. Make a
        change meant to last inside a transaction.

        The lock is held for the whole block, and other writers give up after
        their own timeout, so keep the block short. Do not open one while
        holding :meth:`lock_category`. A transaction does not carry into a child
        forked inside it.

        On a manager without a file, nothing is read or written, and a
        transaction only excludes others on the same manager.

        Args:
            timeout (float): Seconds to wait for the lock, in all; the manager's
                own timeout where None.

        Raises:
            TimeoutError: if the lock is not had in time. Nothing is read or
                written.
            ValueError: if the file is malformed or does not hold a JSON object.
                The file is left as it is: unlike a plain load, which logs and
                starts empty, a transaction will not replace a file it could not
                read.
        """
        if timeout is None:
            timeout = self.__timeout

        if self.__filepath is None:
            if not self.__memory_lock.acquire(timeout=timeout):
                raise TimeoutError(f"Timed out after {timeout}s waiting for a settings "
                                   "transaction: another thread of this process holds it")
            try:
                yield
            finally:
                self.__memory_lock.release()
            return

        with self._locked(timeout):
            depth = getattr(self.__transactions, "depth", 0)
            if depth:
                # Inside this thread's own transaction on this manager, which
                # re-read the file and will save it.
                self.__transactions.depth = depth + 1
                try:
                    yield
                finally:
                    self.__transactions.depth = depth
                return

            try:
                data = self._read()
            except json.JSONDecodeError as e:
                raise ValueError(f"Settings file {self.__filepath} is malformed ({e}); "
                                 "fix or delete it") from e
            if not isinstance(data, dict):
                raise ValueError(f"Settings file {self.__filepath} does not hold a JSON "
                                 "object; fix or delete it")

            # Compared as text, not as dicts, because key order carries
            # meaning (see set): a re-set that only moves a key is a change.
            before = json.dumps(data, indent=4)
            with self.__settings_lock:
                self.__settings = data
            self.__load_error = None

            self.__transactions.depth = 1
            try:
                yield
                after = self._serialize()
                if after != before:
                    self._write(after)
            except BaseException:
                with self.__settings_lock:
                    self.__settings = json.loads(before)
                raise
            finally:
                self.__transactions.depth = 0

    def set(self, category: str, key: str, value, keep: bool = False):
        """
        Set a specific setting within a category.

        A write always places the key last within its category, so a category's
        iteration order is the order its keys were most recently written.
        Categories looked up by key do not care, but the ones whose order
        carries meaning depend on it -- see
        :meth:`~siliconcompiler.tool.OpenTask.register_task`, where a later
        registration has to outrank an earlier one. Leaving a re-written key at
        its original position would silently pin priority to whoever wrote it
        first.

        Args:
            category (str): The group name (e.g., 'showtools', 'options').
            key (str): The specific setting name.
            value: The value to store (must be JSON serializable).
            keep (bool): If True, do not overwrite existing value (and so also
                leave its position alone).
        """
        if self._has_priority(category, key):
            self.__logger.warning(f"Setting '{category}.{key}' has system priority and cannot be "
                                  "overridden. Ignoring.")
            return

        with self._category_lock(category):
            with self.__settings_lock:
                if category not in self.__settings:
                    self.__settings[category] = {}

                if keep and key in self.__settings[category]:
                    return
                # Plain assignment keeps an existing key at its original
                # position; drop it first so the write appends.
                self.__settings[category].pop(key, None)
                self.__settings[category][key] = value

    def get(self, category: str, key: str, default=None):
        """
        Retrieve a setting.

        Resolution order:

        1. If the key has system priority, the system value is returned (or
           ``default`` if the system file does not define it); the user value is
           ignored.
        2. Otherwise, the user value is returned if present.
        3. Otherwise, the (overridable) system default is returned if present.
        4. Otherwise, ``default`` is returned.

        Args:
            category (str): The group name.
            key (str): The specific setting name.
            default: The value to return if the category or key is missing.

        Returns:
            The stored value or the default.
        """
        with self._category_lock(category):
            with self.__settings_lock:
                if self._has_priority(category, key):
                    return self.__system_settings.get(category, {}).get(key, default)

                if category in self.__settings and key in self.__settings[category]:
                    return self.__settings[category][key]

                return self.__system_settings.get(category, {}).get(key, default)

    def get_category(self, category: str):
        """
        Retrieve all settings for a specific category, merging system defaults
        with user overrides.

        System values provide the baseline, user values override them, and
        system-priority keys are forced back to the system value (or removed if
        the system file does not define them). Returns an empty dict if the
        category exists in neither layer.
        """
        with self._category_lock(category):
            with self.__settings_lock:
                return self._merge_category(category)

    def _merge_category(self, category: str):
        """
        Build the effective view of a category. Assumes ``__settings_lock`` is
        held by the caller.
        """
        system_cat = self.__system_settings.get(category, {})

        merged = dict(system_cat)
        merged.update(self.__settings.get(category, {}))

        # Re-apply system-priority values so user values cannot leak through.
        for priority_key in self.__priority.get(category, ()):
            if priority_key in system_cat:
                merged[priority_key] = system_cat[priority_key]
            else:
                merged.pop(priority_key, None)

        return merged

    def delete(self, category: str, key: Optional[str] = None):
        """
        Remove a user setting.

        System-priority settings are administrator-managed and cannot be
        removed; such requests are ignored with a warning. Note that deletion
        only affects the user layer; system defaults remain in effect.
        """
        if key is not None and self._has_priority(category, key):
            self.__logger.warning(f"Setting '{category}.{key}' has system priority and cannot be "
                                  "removed. Ignoring.")
            return

        with self._category_lock(category):
            with self.__settings_lock:
                if category in self.__settings:
                    if key:
                        if key in self.__settings[category]:
                            del self.__settings[category][key]
                            # Clean up empty categories
                            if not self.__settings[category]:
                                del self.__settings[category]
                    else:
                        del self.__settings[category]
