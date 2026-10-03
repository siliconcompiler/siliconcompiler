'''
What this machine holds, and how tightly: ``~/.sc/auth/`` (``SC_AUTH_DIR`` moves it).

``remote.json``    the store: the server, the upload whitelist, and per server
                   its user id, refresh token or CI credential, and operator headers.
``dpop-key.pem``   this machine's private key, **the machine pin itself**, in a
                   file of its own so no rewrite of the store can take it.

🔴 The modes are normative (identity §4): directory ``0700``, files ``0600``,
each created with its mode set. A wider store stops the client rather than
being repaired: the key may already be copied.

🔴 Every change is a transaction that re-reads the file under its lock: writing
back a stale refresh token reads as reuse and ends the session.
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


AUTH_DIRNAME = "auth"
AUTH_DIR_VARIABLE = "SC_AUTH_DIR"

STORE_FILENAME = "remote.json"
KEY_FILENAME = "dpop-key.pem"

CI_SECRET_VARIABLE = "SC_CI_CREDENTIAL"

# A newer store is refused by name rather than misread.
STORE_VERSION = 1

_STORE = "store"        # version, server, directory_whitelist
_SERVERS = "servers"    # each server's entry, by its URL

# A refresh holds the store across its request, which may take 30 seconds.
LOCK_SECONDS = 60

# An older client's configuration file, moved into the store once and removed.
_LEGACY_CONFIG = "credentials"
_LEGACY_FIELDS = ("address", "port", "directory_whitelist")

# The remote client's category in the user's settings.json.
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
        '''Where one project's run looks for its key and session. Not through
        `find_files`, which needs the file to exist: `-configure` creates it.'''
        from siliconcompiler import utils

        configured = project.option.get_credentials()
        if configured:
            return cls(Path(configured).expanduser().absolute())
        return cls(Path(utils.default_credentials_file()))

    def __init__(self, path: Path):
        '''``path`` is the store file, `option,credentials`; an older client's
        configuration file there is moved into ``auth/`` beside it.'''
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
        '''Use the store in ``auth_dir`` instead; nothing is copied, so its key is new.'''
        self._open(Path(auth_dir) / STORE_FILENAME)

    ######################################################################
    # Reading
    ######################################################################

    @property
    def server(self) -> Optional[str]:
        '''The configured server's base URL, which keys its entry.'''
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
        '''The `id` GET /v1/me last reported for this server. Not a credential:
        kept so a changed principal can be told apart from deleted jobs.'''
        return self._entry().get("user_id")

    @property
    def refresh_token(self) -> Optional[str]:
        return self._entry().get("refresh_token")

    def headers(self) -> Dict[str, str]:
        '''The operator-configured headers for this server. Secret values.'''
        return dict(self._entry().get("headers") or {})

    def ci_secret(self) -> Optional[str]:
        '''The one-line CI secret: the environment first, then this server's entry.'''
        value = os.environ.get(CI_SECRET_VARIABLE)
        if value:
            return value.strip()
        return self._entry().get("ci_credential") or None

    ######################################################################
    # Changing
    ######################################################################

    @contextlib.contextmanager
    def transaction(self):
        '''Hold the store for one change: re-read under its lock, saved on a
        clean exit. Nests. Raises `StoreError` if locked too long, unreadable or newer.'''
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
        '''Point this machine at a server; switching back finds its entry intact.'''
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
        '''Persist the refresh token; the access token is never written down.'''
        self._update_entry(refresh_token=body.get("refresh_token"))

    def forget_tokens(self) -> None:
        self._update_entry(refresh_token=None)

    def set_header(self, name: str, value: Optional[str]) -> None:
        '''Set an operator header for this server, or remove it with None. No
        line breaks: the value is sent verbatim on every request.'''
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
        '''Store this server's CI credential in place of a refresh token.'''
        parse_ci_secret(secret)
        self._update_entry(ci_credential=secret.strip(), refresh_token=None)

    ######################################################################
    # The key
    ######################################################################

    @property
    def key_path(self) -> Path:
        return self.auth_dir / KEY_FILENAME

    def key(self):
        '''This machine's private key, generated locally on first use.

        🔴 No error ever replaces it: it is the device pin; only `rotate_key` does.
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
        '''Replace the key, dropping every refresh token bound to it; ids, headers
        and CI credentials stay.'''
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
        '''🔴 Refuse a store others can read, rather than repair it: the directory
        and the store's own files in it.'''
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
        '''Whether a file is the store's: the store, its lock, the key, or their temporaries.'''
        store = self.path.name
        if name in (store, f"{store}.lock", f"{store}.sc_lock", KEY_FILENAME):
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
    # What an older client left
    ######################################################################

    def _migrate(self, config: Optional[Path]) -> None:
        '''Move an older client's server and whitelist into the store, once.'''
        from siliconcompiler.remote.client.transport import normalize_server

        if config is None:
            return
        values = _read_json(config)

        with self.transaction():
            if values.get("address") and not self.server:
                self._store.set(_STORE, "server",
                                normalize_server(values["address"], values.get("port")))
            if values.get("directory_whitelist") and not self.directory_whitelist:
                self._store.set(_STORE, "directory_whitelist",
                                list(values["directory_whitelist"]))

        config.unlink(missing_ok=True)
        logger.info(f"Moved the remote configuration into {self.path}")


def preference(name: str, default: Any = None) -> Any:
    '''One of the remote client's preferences, from the user's settings.json.'''
    from siliconcompiler.utils.multiprocessing import MPManager

    return MPManager.get_settings().get(SETTINGS_CATEGORY, name, default)


def _resolve(given: Path) -> Tuple[Path, Optional[Path]]:
    '''``(store file, legacy configuration to move in or None)`` for the path
    `option,credentials` names. A legacy file's store is ``auth/remote.json``
    beside it, which is also used once the file is gone.
    '''
    if given.exists():
        if _is_legacy_config(given):
            return given.parent / AUTH_DIRNAME / STORE_FILENAME, given
        return given, None

    beside = given.parent / AUTH_DIRNAME / STORE_FILENAME
    if given.name != STORE_FILENAME and beside.exists():
        logger.warning(f"{given} was moved into {beside}: point -credentials there")
        return beside, None

    # A store named directly may still have a legacy file above it to move in.
    if given.parent.name == AUTH_DIRNAME:
        old = given.parent.parent / _LEGACY_CONFIG
        if old.exists() and _is_legacy_config(old):
            return given, old
    return given, None


def _is_legacy_config(path: Path) -> bool:
    '''Whether ``path`` is an older client's configuration file.'''
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
    The base64url key may contain `_`, so only the first two separate.'''
    from cryptography.hazmat.primitives.serialization import load_der_private_key
    from jwt.utils import base64url_decode

    parts = (secret or "").strip().split("_", 2)
    if len(parts) != 3 or not all(parts):
        raise RemoteError(f"{CI_SECRET_VARIABLE} is not a CI credential: it is one line, "
                          "<prefix>_<credential id>_<key>")
    _, credential_id, encoded = parts
    try:
        key = load_der_private_key(base64url_decode(encoded), password=None)
    except Exception:                                           # noqa: BLE001
        raise RemoteError(f"the key in {CI_SECRET_VARIABLE} does not decode") from None
    return credential_id, key


def _write_atomic(path, payload: bytes, mode: int = _PRIVATE_FILE) -> None:
    '''Write through a temporary file created with ``mode``, renamed over the
    target: never truncated, and a private file never briefly readable.'''
    from siliconcompiler.utils.settings import _create_temp, _replace

    fd, temporary = _create_temp(str(path), mode)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        _replace(temporary, str(path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def _restrict_windows(path: Path) -> None:                      # pragma: no cover
    '''The Windows equivalent of 0700: an inherited ACL granting the user alone.'''
    import getpass
    import subprocess

    subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                    f"{getpass.getuser()}:(OI)(CI)F"],
                   check=True, capture_output=True)
