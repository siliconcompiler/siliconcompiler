'''
What this machine holds, and how tightly.

Two places, and only one of them is secret:

``~/.sc/credentials``   which server, the upload whitelist, and the id the
                        server last knew this machine by. Not a secret.
``~/.sc/auth/``         the session store: the DPoP private key -- **the machine
                        pin itself** -- each server's refresh token, and any
                        operator header secret.

🔴 **The store's modes are normative** (identity §4): the directory is ``0700``
and every file in it ``0600``, each created with its mode set, never ``open()``
then ``chmod()``. A store found wider than that stops the client rather than
being repaired: a key that was readable by others may already be copied, so the
user is told to fix the modes and rotate the key.

🔴 **The access token is deliberately NOT written down.** It lives minutes and
this store lives for weeks, so a stored one is stale far more often than it is
useful. What is kept is bound to the key beside it: the server pins a session
to a thumbprint and checks it on every refresh.

The store is a directory of its own for one reason: ``scheduler/docker.py``
mounts ``~/.sc`` into task containers, and one path is something a narrower
mount can leave out.
'''

import contextlib
import json
import os
import stat
import sys

from pathlib import Path
from typing import Any, Dict, Optional

from siliconcompiler.remote import dpop
from siliconcompiler.remote.client.errors import RemoteError

__all__ = ["Credentials", "StoreError", "AUTH_DIRNAME", "KEY_FILENAME",
           "CI_SECRET_VARIABLE", "parse_ci_secret"]


# The session store, beside the configuration file unless SC_AUTH_DIR moves it
# -- which is how a CI job keeps what it writes in a job-scoped directory.
AUTH_DIRNAME = "auth"
AUTH_DIR_VARIABLE = "SC_AUTH_DIR"

KEY_FILENAME = "dpop-key.pem"
SESSIONS_FILENAME = "sessions.json"      # per server: refresh token, scope, grants
HEADERS_FILENAME = "headers.json"        # per origin: operator header secrets
CI_FILENAME = "ci-credential"            # the one-line CI secret, from -ci_setup
LOCK_FILENAME = "lock"

# Where a CI job's one-line credential secret is read from.
CI_SECRET_VARIABLE = "SC_CI_CREDENTIAL"

# What a client of an older release left in ~/.sc, moved into the store.
_LEGACY_KEY_FILENAME = "credentials.key"

_PRIVATE_DIR = 0o700
_PRIVATE_FILE = 0o600


class StoreError(RemoteError):
    '''The session store is not safe to use as it stands.'''


class Credentials:
    '''One machine's configuration, and its session store.'''

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
        self.path = Path(path)
        self.auth_dir = Path(os.environ.get(AUTH_DIR_VARIABLE)
                             or self.path.parent / AUTH_DIRNAME)
        self._values: Dict[str, Any] = {}
        self._key = None

        if self.path.exists():
            self._values = json.loads(self.path.read_text() or "{}")

        # Dropped on read, not just on write: a file written by a client that
        # persisted one must not have it read back.
        self._values.pop("access_token", None)

        self.check_store()
        self._migrate()

    ######################################################################
    # Reading
    ######################################################################

    @property
    def address(self) -> Optional[str]:
        return self._values.get("address")

    @property
    def port(self) -> Optional[int]:
        return self._values.get("port")

    @property
    def server(self) -> Optional[str]:
        '''The base URL of the configured server: what the store is keyed by.'''
        if not self.address:
            return None
        from siliconcompiler.remote.client.transport import normalize_server
        return normalize_server(self.address, self.port)

    @property
    def refresh_token(self) -> Optional[str]:
        return self.session_value("refresh_token")

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
        return self._values.get("user_id")

    @property
    def directory_whitelist(self) -> list:
        return list(self._values.get("directory_whitelist", []))

    def get(self, name: str, default: Any = None) -> Any:
        return self._values.get(name, default)

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
        enrols again as a new device.
        '''
        with self.lock():
            self._key = dpop.generate_key()
            self._write(self.key_path, dpop.serialize_key(self._key))
            self._write_json(SESSIONS_FILENAME, {})

    ######################################################################
    # The session, per server
    ######################################################################

    def sessions(self) -> Dict[str, Dict[str, Any]]:
        return self._read_json(SESSIONS_FILENAME)

    def session_value(self, name: str, default: Any = None) -> Any:
        return (self.sessions().get(self.server or "") or {}).get(name, default)

    def update_session(self, **values) -> None:
        '''Write this server's entry, through a temporary file and a rename.'''
        if not self.server:
            return
        sessions = self.sessions()
        entry = dict(sessions.get(self.server) or {})
        for name, value in values.items():
            if value is None:
                entry.pop(name, None)
            else:
                entry[name] = value
        sessions[self.server] = entry
        self._write_json(SESSIONS_FILENAME, sessions)

    def save_tokens(self, body: Dict[str, Any]) -> None:
        '''Persist the half of a session that outlives this command: the
        refresh token, and the scope it was granted.'''
        self.update_session(refresh_token=body.get("refresh_token"),
                            scope=body.get("scope"))

    def forget_tokens(self) -> None:
        self.update_session(refresh_token=None, scope=None)

    ######################################################################
    # Operator headers and the CI secret
    ######################################################################

    def headers_for(self, origin: str) -> Dict[str, str]:
        '''The operator-configured headers for one origin. Secret values.'''
        return dict(self._read_json(HEADERS_FILENAME).get(_origin(origin)) or {})

    def configured_origins(self):
        return set(self._read_json(HEADERS_FILENAME))

    def set_header(self, origin: str, name: str, value: Optional[str]) -> None:
        import re

        # A header name is an RFC 9110 token, and neither half may carry a line
        # break: a value is sent verbatim on every request to the origin.
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name or ""):
            raise StoreError(f"{name!r} is not a header name")
        if name.lower() in ("authorization", "dpop", "host", "content-length",
                            "content-type", "cookie"):
            raise StoreError(f"{name} is set by this client and cannot be configured")
        if value is not None and any(c in value for c in "\r\n\0"):
            raise StoreError(f"the value for {name} contains a line break")
        headers = self._read_json(HEADERS_FILENAME)
        entry = dict(headers.get(_origin(origin)) or {})
        if value is None:
            entry.pop(name, None)
        else:
            entry[name] = value
        if entry:
            headers[_origin(origin)] = entry
        else:
            headers.pop(_origin(origin), None)
        self._write_json(HEADERS_FILENAME, headers)

    def ci_secret(self) -> Optional[str]:
        '''The one-line CI secret: the environment first, then the store.'''
        value = os.environ.get(CI_SECRET_VARIABLE)
        if value:
            return value.strip()
        path = self.auth_dir / CI_FILENAME
        if path.exists():
            return path.read_text().strip() or None
        return None

    def save_ci_secret(self, secret: str) -> None:
        parse_ci_secret(secret)
        self._write(self.auth_dir / CI_FILENAME, (secret.strip() + "\n").encode())

    ######################################################################
    # The configuration file
    ######################################################################

    def update(self, **values) -> None:
        for name, value in values.items():
            if name in ("access_token", "refresh_token"):
                # Neither belongs in the configuration file any more.
                continue
            if value is None:
                self._values.pop(name, None)
            else:
                self._values[name] = value
        self.save()

    def save(self) -> None:
        self._values.setdefault("directory_whitelist", [])
        self._values.pop("refresh_token", None)
        _write_atomic(self.path, (json.dumps(self._values, indent=2) + "\n").encode("utf-8"))

    ######################################################################
    # One refresh at a time
    ######################################################################

    @contextlib.contextmanager
    def lock(self):
        '''An inter-process lock on the store, for one refresh at a time.

        A process that waited MUST re-read the store once it holds this, never
        use the token it held before.
        '''
        import fasteners

        self._ensure_dir()
        path = self.auth_dir / LOCK_FILENAME
        if not path.exists():
            # Created with its mode, so the lock file is no exception.
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT, _PRIVATE_FILE)
            os.close(fd)
        with fasteners.InterProcessLock(str(path)):
            yield

    ######################################################################
    # The store's files
    ######################################################################

    def check_store(self) -> None:
        '''🔴 Refuse a store others can read, rather than repair it.'''
        if sys.platform == "win32" or not self.auth_dir.exists():
            return
        wrong = []
        if stat.S_IMODE(os.stat(self.auth_dir).st_mode) & 0o077:
            wrong.append(str(self.auth_dir))
        for entry in self.auth_dir.iterdir():
            if stat.S_IMODE(os.lstat(entry).st_mode) & 0o077 or entry.is_symlink():
                wrong.append(str(entry))
        if wrong:
            raise StoreError(
                f"the session store is readable by others: {', '.join(wrong)}. "
                f"Fix it -- chmod 700 {self.auth_dir}; chmod 600 on every file in "
                "it -- and then rotate this machine's key with sc-remote -rotate_key, "
                "because a key others could read may already be copied")

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

    def _read_json(self, name: str) -> Dict[str, Any]:
        path = self.auth_dir / name
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text() or "{}")
        except ValueError:
            return {}
        return value if isinstance(value, dict) else {}

    def _write_json(self, name: str, value: Dict[str, Any]) -> None:
        self._write(self.auth_dir / name,
                    (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())

    def _migrate(self) -> None:
        '''Move an older client's secrets into the store, once.

        The key file and the refresh token lived beside the configuration; both
        go into the store, and neither is left behind.
        '''
        legacy_key = self.path.parent / _LEGACY_KEY_FILENAME
        refresh = self._values.get("refresh_token")
        if not legacy_key.exists() and not refresh:
            return
        if legacy_key.exists() and not self.key_path.exists():
            self._write(self.key_path, legacy_key.read_bytes())
        if legacy_key.exists():
            legacy_key.unlink()
        if refresh and self.server and not self.refresh_token:
            self.update_session(refresh_token=refresh)
        if "refresh_token" in self._values:
            self.save()


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


def _origin(url: str) -> str:
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.netloc else url.rstrip("/")


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
