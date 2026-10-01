'''
What this machine holds, and how tightly.

One directory, ``~/.sc/auth/`` (``SC_AUTH_DIR`` moves it), and in it two files:

``remote.json``    the store: which server, the upload whitelist, and for each
                   server the id it last knew this machine by, its refresh
                   token or its CI credential, and any operator header secret.
``dpop-key.pem``   this machine's private key -- **the machine pin itself** --
                   a file of its own, so that no rewrite of the store can take
                   it.

``remote.json`` is a :class:`~siliconcompiler.utils.settings.SettingsManager`
file in two categories::

    {"store":   {"version": 1,
                 "server": "https://sc.example.com/v1",
                 "directory_whitelist": []},
     "servers": {"https://sc.example.com/v1": {"user_id": "...",
                                                "refresh_token": "...",
                                                "headers": {"CF-Access-Client-Id": "..."}}}}

A server's entry holds ``refresh_token``, for an interactive session, or
``ci_credential``, for a CI one, which trades it for each access token -- never
both. No access token is kept, so a command spends the refresh token once.
``version`` is the store's own: a later client migrates an older file, and this
one refuses a newer one by name rather than misreading it.

🔴 **The store's modes are normative** (identity §4): the directory is ``0700``
and every file in it ``0600``, each created with its mode set, never ``open()``
then ``chmod()``. A store found wider than that stops the client rather than
being repaired: a key that was readable by others may already be copied, so the
user is told to fix the modes and rotate the key.

🔴 **Every change is a transaction** that re-reads the file under its lock
first. A refresh token is rotated by one process at a time: a second process
writing back the copy it read earlier would put back a spent token, which the
server reads as reuse, and ends the session.

The store is a directory of its own for one reason: ``scheduler/docker.py``
mounts ``~/.sc`` into task containers, and one path is something a narrower
mount can leave out.
'''

import contextlib
import json
import logging
import os
import stat
import sys

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from siliconcompiler.remote import dpop
from siliconcompiler.remote.client.errors import RemoteError

__all__ = ["Credentials", "StoreError", "AUTH_DIRNAME", "STORE_FILENAME", "KEY_FILENAME",
           "CI_SECRET_VARIABLE", "parse_ci_secret"]


# The store's directory, beside SiliconCompiler's own configuration unless
# SC_AUTH_DIR moves it -- which is how a CI job keeps what it writes in a
# job-scoped directory.
AUTH_DIRNAME = "auth"
AUTH_DIR_VARIABLE = "SC_AUTH_DIR"

STORE_FILENAME = "remote.json"
KEY_FILENAME = "dpop-key.pem"

# Where a CI job's one-line credential secret is read from.
CI_SECRET_VARIABLE = "SC_CI_CREDENTIAL"

# The store's own version. A change to its shape is a new number, with a
# migration from the last.
STORE_VERSION = 1

# The two categories.
_STORE = "store"        # version, server, directory_whitelist
_SERVERS = "servers"    # each server's entry, by its URL

# How long a change waits for another process's. A refresh holds the store
# across its request, which the transport gives 30 seconds.
LOCK_SECONDS = 60

# What older clients left, moved into the store once and removed: a
# configuration file beside the store's directory, and three files and a lock
# inside it.
_LEGACY_CONFIG = "credentials"
_LEGACY_SESSIONS = "sessions.json"
_LEGACY_HEADERS = "headers.json"
_LEGACY_CI = "ci-credential"
_LEGACY_LOCKS = ("lock", "sessions.json.lock")
_LEGACY_KEY = "credentials.key"         # beside the old configuration file
# The keys an old configuration file held.
_LEGACY_FIELDS = ("address", "port", "directory_whitelist", "user_id", "refresh_token",
                  "access_token", "open_portal")

# Where a preference the old configuration file held now lives: the user's
# settings.json.
SETTINGS_CATEGORY = "remote"

_PRIVATE_DIR = 0o700
_PRIVATE_FILE = 0o600

logger = logging.getLogger(__name__)


class StoreError(RemoteError):
    '''The session store is not safe to use as it stands.'''


class Credentials:
    '''One machine's remote configuration, and its sessions.'''

    @classmethod
    def for_project(cls, project) -> "Credentials":
        '''Where one project's run looks for its key and its session.

        The path is taken as given rather than resolved through `find_files`,
        which requires the file to exist -- and creating it is exactly what
        `sc-remote -configure` is for.
        '''
        from siliconcompiler import utils

        configured = project.option.get_credentials()
        if configured:
            return cls(Path(configured).expanduser().absolute())
        return cls(Path(utils.default_credentials_file()))

    def __init__(self, path: Path):
        '''``path`` is the store file, `option,credentials`. An older client's
        configuration file named there is moved into the ``auth/`` beside it.'''
        store, legacy = _resolve(Path(path))
        if os.environ.get(AUTH_DIR_VARIABLE):
            store = Path(os.environ[AUTH_DIR_VARIABLE]) / STORE_FILENAME
        self._open(store)
        self._migrate(legacy)

    def _open(self, path: Path) -> None:
        from siliconcompiler.utils.settings import SettingsManager

        self.path = Path(path)
        self.auth_dir = self.path.parent
        self._key = None
        self.check_store()
        self._ensure_dir()
        self._store = SettingsManager(str(self.path), logger, timeout=LOCK_SECONDS,
                                      mode=_PRIVATE_FILE)
        self._check_version()

    def relocate(self, auth_dir: Path) -> None:
        '''Use the store in ``auth_dir`` instead, as a CI job does in its own
        temporary directory. Nothing is copied: a store moved is a new one, and
        its key is generated there.'''
        self._open(Path(auth_dir) / STORE_FILENAME)

    ######################################################################
    # Reading
    ######################################################################

    @property
    def server(self) -> Optional[str]:
        '''The base URL of the configured server: what each entry is keyed by.'''
        return self._store.get(_STORE, "server")

    @property
    def directory_whitelist(self) -> list:
        return list(self._store.get(_STORE, "directory_whitelist") or [])

    def _entry(self, server: Optional[str] = None) -> Dict[str, Any]:
        server = server or self.server
        if not server:
            return {}
        return dict(self._store.get(_SERVERS, server) or {})

    @property
    def user_id(self) -> Optional[str]:
        '''The `id` GET /v1/me last reported for this server.

        **Not a credential, and it authenticates nothing.** Persisted because it
        is the one thing here that CANNOT be fetched when it is needed: *who did
        this server say I was last time*. A reimage, a rebuilt container, a CI
        image, a changed uid and a client release that moves the derivation salt
        all replace the principal, and all look like "every job I ever ran has
        been deleted" without it.
        '''
        return self._entry().get("user_id")

    @property
    def refresh_token(self) -> Optional[str]:
        return self._entry().get("refresh_token")

    def headers(self) -> Dict[str, str]:
        '''The operator-configured headers for this server. Secret values.'''
        return dict(self._entry().get("headers") or {})

    def ci_secret(self) -> Optional[str]:
        '''The one-line CI secret: the environment first, then this server's
        entry.'''
        value = os.environ.get(CI_SECRET_VARIABLE)
        if value:
            return value.strip()
        return self._entry().get("ci_credential") or None

    ######################################################################
    # Changing
    ######################################################################

    @contextlib.contextmanager
    def transaction(self):
        '''Hold the store for one change: the file is re-read under its lock
        first, so what this sees is what another process last wrote, and saved
        on a clean exit. A refresh holds it across its request, so a process
        that waited uses the token the refresh wrote, never the one it held.

        Nests: a change made inside another joins it.

        Raises:
            StoreError: where the store is held past `LOCK_SECONDS`, does not
                read, or was written by a newer client.
        '''
        self._ensure_dir()
        entered = False
        try:
            with self._store.transaction(timeout=LOCK_SECONDS):
                entered = True
                self._check_version()
                if self._store.get(_STORE, "version") is None:
                    self._store.set(_STORE, "version", STORE_VERSION)
                yield
        except (TimeoutError, ValueError) as e:
            if entered:
                raise
            raise StoreError(f"the session store {self.path} cannot be used: {e}") from None

    def set_server(self, server: str) -> None:
        '''Point this machine at a server, by its address or base URL, kept as
        the base URL. Each server keeps its own entry, so switching back finds
        the session left there.'''
        from siliconcompiler.remote.client.transport import normalize_server

        with self.transaction():
            self._store.set(_STORE, "server", normalize_server(server))

    def set_directory_whitelist(self, entries) -> None:
        with self.transaction():
            self._store.set(_STORE, "directory_whitelist", list(entries))

    def _update_entry(self, **values) -> None:
        '''This server's entry, changed: a value of None removes its field.'''
        server = self.server
        if not server:
            return
        with self.transaction():
            entry = self._entry(server)
            for name, value in values.items():
                if value is None:
                    entry.pop(name, None)
                else:
                    entry[name] = value
            self._store.set(_SERVERS, server, entry)

    def set_user_id(self, user_id: Optional[str]) -> None:
        if user_id != self.user_id:
            self._update_entry(user_id=user_id)

    def save_tokens(self, body: Dict[str, Any]) -> None:
        '''Persist the half of a session that outlives this command: the
        refresh token. The access token is never written down.'''
        self._update_entry(refresh_token=body.get("refresh_token"))

    def forget_tokens(self) -> None:
        self._update_entry(refresh_token=None)

    def set_header(self, name: str, value: Optional[str]) -> None:
        '''An operator-configured header for this server, or None to remove
        it. A header name is an RFC 9110 token, and neither half may carry a
        line break: a value is sent verbatim on every request to the server.'''
        import re

        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name or ""):
            raise StoreError(f"{name!r} is not a header name")
        if name.lower() in ("authorization", "dpop", "host", "content-length",
                            "content-type", "cookie"):
            raise StoreError(f"{name} is set by this client and cannot be configured")
        if value is not None and any(c in value for c in "\r\n\0"):
            raise StoreError(f"the value for {name} contains a line break")
        if not self.server:
            raise StoreError("no server is configured: run sc-remote -configure first")
        headers = self.headers()
        if value is None:
            headers.pop(name, None)
        else:
            headers[name] = value
        self._update_entry(headers=headers or None)

    def save_ci_secret(self, secret: str) -> None:
        '''This server's CI credential, in place of a refresh token: a CI
        session trades the credential for each access token.'''
        parse_ci_secret(secret)
        self._update_entry(ci_credential=secret.strip(), refresh_token=None)

    ######################################################################
    # The key
    ######################################################################

    @property
    def key_path(self) -> Path:
        return self.auth_dir / KEY_FILENAME

    def key(self):
        '''This machine's private key, generated on first use.

        Generated locally and never sent anywhere. 🔴 **No error ever replaces
        it**: it is the device pin, and only `rotate_key` does.
        '''
        if self._key is not None:
            return self._key

        if self.key_path.exists():
            self._key = dpop.load_key(self.key_path.read_bytes())
            return self._key

        self._key = dpop.generate_key()
        self._write(self.key_path, dpop.serialize_key(self._key))
        return self._key

    @property
    def thumbprint(self) -> str:
        '''The `jkt` the server knows this machine by.'''
        return dpop.jwk_thumbprint(dpop.public_jwk(self.key()))

    def rotate_key(self) -> None:
        '''Replace the key, and with it every session it was bound to.

        The deliberate act the contract reserves the key for: the machine
        enrols again as a new device. Each server's refresh token goes with
        it; its id, its headers and a CI credential, which no key binds, stay.
        '''
        with self.transaction():
            self._key = dpop.generate_key()
            self._write(self.key_path, dpop.serialize_key(self._key))
            for server, entry in (self._store.get_category(_SERVERS) or {}).items():
                if isinstance(entry, dict) and "refresh_token" in entry:
                    entry = dict(entry)
                    entry.pop("refresh_token")
                    self._store.set(_SERVERS, server, entry)

    ######################################################################
    # The store's files
    ######################################################################

    def check_store(self) -> None:
        '''🔴 Refuse a store others can read, rather than repair it: its
        directory, which holds the key, and each of the store's own files in
        it. A file of anything else's in a private directory is not the
        store's to judge.'''
        if sys.platform == "win32" or not self.auth_dir.exists():
            return
        wrong = []
        if stat.S_IMODE(os.stat(self.auth_dir).st_mode) & 0o077:
            wrong.append(str(self.auth_dir))
        for entry in self.auth_dir.iterdir():
            if not self._owns(entry.name):
                continue
            if stat.S_IMODE(os.lstat(entry).st_mode) & 0o077 or entry.is_symlink():
                wrong.append(str(entry))
        if wrong:
            raise StoreError(
                f"the session store is readable by others: {', '.join(wrong)}. "
                f"Fix it -- chmod 700 {self.auth_dir}; chmod 600 on every file in "
                "it -- and then rotate this machine's key with sc-remote -rotate_key, "
                "because a key others could read may already be copied")

    def _owns(self, name: str) -> bool:
        '''Whether a file in the store's directory is the store's: the store,
        its lock, the key, a temporary file either is written through, or a
        file an older client left there.'''
        store = self.path.name
        if name in (store, f"{store}.lock", f"{store}.sc_lock", KEY_FILENAME,
                    _LEGACY_SESSIONS, _LEGACY_HEADERS, _LEGACY_CI, *_LEGACY_LOCKS):
            return True
        return name.endswith(".tmp") and name.startswith((f".{store}.", f".{KEY_FILENAME}."))

    def _check_version(self) -> None:
        version = self._store.get(_STORE, "version")
        if version is None:
            return
        if not isinstance(version, int) or isinstance(version, bool):
            raise StoreError(f"{self.path} names no store version this client reads")
        if version > STORE_VERSION:
            raise StoreError(
                f"{self.path} was written by a newer SiliconCompiler (store version "
                f"{version}; this one reads {STORE_VERSION}). Upgrade SiliconCompiler, "
                "or point -credentials at another store")

    def _ensure_dir(self) -> None:
        if self.auth_dir.exists():
            return
        self.auth_dir.parent.mkdir(parents=True, exist_ok=True)
        os.mkdir(self.auth_dir, _PRIVATE_DIR)
        if sys.platform == "win32":                             # pragma: no cover
            _restrict_windows(self.auth_dir)

    def _write(self, path: Path, payload: bytes) -> None:
        self._ensure_dir()
        _write_atomic(path, payload)

    ######################################################################
    # What older clients left
    ######################################################################

    def _migrate(self, config: Optional[Path]) -> None:
        '''Move an older client's files into the store, once, and remove them.

        From the configuration file: the server, the whitelist and the id it
        last reported, and `open_portal`, a preference, into the user's
        settings. From the old store's directory: each server's refresh token,
        each origin's headers into the server on that origin, and the CI
        credential into the configured server, in place of its refresh token.
        A key file that predates the store becomes the key.
        '''
        from siliconcompiler.remote.client.transport import normalize_server, origin_of

        values = _read_json(config) if config is not None else {}
        sessions = _read_json(self.auth_dir / _LEGACY_SESSIONS)
        headers = _read_json(self.auth_dir / _LEGACY_HEADERS)
        ci_path = self.auth_dir / _LEGACY_CI
        ci = ci_path.read_text().strip() if ci_path.exists() else ""
        legacy_key = config.parent / _LEGACY_KEY if config is not None else None
        leftovers = [self.auth_dir / name for name in _LEGACY_LOCKS]
        if not (values or sessions or headers or ci or any(p.exists() for p in leftovers)
                or (legacy_key is not None and legacy_key.exists())):
            return

        if legacy_key is not None and legacy_key.exists() and not self.key_path.exists():
            self._write(self.key_path, legacy_key.read_bytes())

        with self.transaction():
            if values.get("address") and not self.server:
                self._store.set(_STORE, "server",
                                normalize_server(values["address"], values.get("port")))
            if values.get("directory_whitelist") and not self.directory_whitelist:
                self._store.set(_STORE, "directory_whitelist",
                                list(values["directory_whitelist"]))
            server = self.server
            entries = {url: dict(entry) for url, entry
                       in (self._store.get_category(_SERVERS) or {}).items()
                       if isinstance(entry, dict)}
            for url, old in sessions.items():
                if isinstance(old, dict) and old.get("refresh_token"):
                    entries.setdefault(url, {}).setdefault("refresh_token", old["refresh_token"])
            if server:
                if values.get("user_id"):
                    entries.setdefault(server, {}).setdefault("user_id", values["user_id"])
                if values.get("refresh_token"):
                    entries.setdefault(server, {}).setdefault("refresh_token",
                                                              values["refresh_token"])
                if ci:
                    entries.setdefault(server, {})["ci_credential"] = ci
                    entries[server].pop("refresh_token", None)
            for origin, named in headers.items():
                if not isinstance(named, dict):
                    continue
                for url in [url for url in {*entries, *([server] if server else [])}
                            if origin_of(url) == origin]:
                    entries.setdefault(url, {}).setdefault("headers", {}).update(named)
            for url, entry in entries.items():
                self._store.set(_SERVERS, url, entry)

        if values.get("open_portal") is not None:
            _set_preference("open_portal", values["open_portal"])

        for stale in [config, self.auth_dir / _LEGACY_SESSIONS, self.auth_dir / _LEGACY_HEADERS,
                      ci_path, legacy_key, *leftovers]:
            if stale is not None and stale.exists():
                stale.unlink()
        logger.info(f"Moved the remote configuration into {self.path}")


def preference(name: str, default: Any = None) -> Any:
    '''One of the remote client's preferences, from the user's settings.json.'''
    from siliconcompiler.utils.multiprocessing import MPManager

    return MPManager.get_settings().get(SETTINGS_CATEGORY, name, default)


def _set_preference(name: str, value: Any) -> None:
    from siliconcompiler.utils.multiprocessing import MPManager

    settings = MPManager.get_settings()
    with settings.transaction():
        settings.set(SETTINGS_CATEGORY, name, value)


def _resolve(given: Path) -> Tuple[Path, Optional[Path]]:
    '''``(the store file, an older client's configuration file to move into
    it, or None)`` for the path `option,credentials` names.

    - **A store file**, or nothing yet: it is the store.
    - **An older client's configuration file**, `~/.sc/credentials` or one of
      its shape: the store is ``auth/remote.json`` beside it, and the file is
      moved in.
    - **A path that is gone, with a store beside it**: the configuration file
      that was moved, still named by a script. That store is used.
    '''
    if given.exists():
        if _is_legacy_config(given):
            return given.parent / AUTH_DIRNAME / STORE_FILENAME, given
        return given, None

    beside = given.parent / AUTH_DIRNAME / STORE_FILENAME
    if given.name != STORE_FILENAME and beside.exists():
        logger.warning(f"{given} was moved into {beside}: point -credentials there")
        return beside, None

    # A store named directly: an older client's configuration file left in
    # the directory above its own may still need moving in.
    if given.parent.name == AUTH_DIRNAME:
        old = given.parent.parent / _LEGACY_CONFIG
        if old.exists() and _is_legacy_config(old):
            return given, old
    return given, None


def _is_legacy_config(path: Path) -> bool:
    '''Whether ``path`` is an older client's configuration file: a JSON object
    of its fields, with no store category.'''
    values = _read_json(path)
    return bool(values) and _STORE not in values and \
        any(name in values for name in _LEGACY_FIELDS)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text() or "{}")
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def parse_ci_secret(secret: str):
    '''``<prefix>_<credential id>_<key>`` into ``(credential id, private key)``.

    The key is the credential's EC P-256 private key as PKCS#8 DER, base64url
    without padding -- which may itself contain `_`, so only the first two
    separate.
    '''
    import base64

    from cryptography.hazmat.primitives.serialization import load_der_private_key

    parts = (secret or "").strip().split("_", 2)
    if len(parts) != 3 or not all(parts):
        raise RemoteError(f"{CI_SECRET_VARIABLE} is not a CI credential: it is one line, "
                          "<prefix>_<credential id>_<key>")
    _, credential_id, encoded = parts
    try:
        der = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        key = load_der_private_key(der, password=None)
    except Exception:                                           # noqa: BLE001
        raise RemoteError(f"the key in {CI_SECRET_VARIABLE} does not decode") from None
    return credential_id, key


def _write_atomic(path: Path, payload: bytes) -> None:
    '''Write through a temporary file in the same directory, created with the
    mode set, and rename it over the target. The live file is never truncated,
    and its contents are never readable by anyone else, not even briefly.'''
    import secrets

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, _PRIVATE_FILE)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _restrict_windows(path: Path) -> None:                      # pragma: no cover
    '''The Windows equivalent of 0700: an access-control list granting the
    user alone, inherited by every file created in the directory.'''
    import getpass
    import subprocess

    subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                    f"{getpass.getuser()}:(OI)(CI)F"],
                   check=True, capture_output=True)
