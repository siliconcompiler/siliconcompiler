'''
What this machine holds, and how tightly.

Three things live here and they are not equally sensitive:

``address``        which server. Not a secret.
``dpop_key``       the private key. **The machine pin itself.**
``refresh_token``  a session, spendable only by something holding that key.

The file this replaces held a password and was made ``0600`` by a shipped fix.
That mode is a floor, not a starting point: a long-lived refresh token is a
session rather than one service's password, and a DPoP private key is the pin.

🔴 **The access token is deliberately NOT written down.** It lives fifteen
minutes and this file lives for weeks, so a stored one is stale far more often
than it is useful -- the client would present a dead token, take a 401 and
refresh anyway. Keeping it in memory for the length of one command costs a
refresh at the start of the next and removes a credential from disk entirely.
What is left is bound to the key beside it: the server pins a token family to a
thumbprint and checks it on every refresh, so this file without
``credentials.key`` spends nothing.

The key is kept beside the credentials rather than inside them, in its own
``0600`` file, for one reason: ``scheduler/docker.py`` mounts ``~/.sc`` into task
containers, and a separate file is something a narrower mount can exclude. A key
baked into the credentials JSON cannot be left out of that mount without leaving
out the address too.
'''

import json
import os
import stat
import sys

from pathlib import Path
from typing import Any, Dict, Optional

from siliconcompiler.remote import dpop

__all__ = ["Credentials", "KEY_FILENAME"]


# Beside the credentials file, not inside it.
KEY_FILENAME = "credentials.key"

_PRIVATE = 0o600


class Credentials:
    '''One machine's configuration for one server.'''

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
        self.key_path = self.path.parent / KEY_FILENAME
        self._values: Dict[str, Any] = {}
        self._key = None

        if self.path.exists():
            self._values = json.loads(self.path.read_text())

        # Dropped on read, not just on write: a file written by a client that
        # persisted one must not have it read back, and popping it here means
        # no later save can put it back.
        self._values.pop("access_token", None)

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
    def refresh_token(self) -> Optional[str]:
        return self._values.get("refresh_token")

    @property
    def user_id(self) -> Optional[str]:
        '''The `id` GET /v1/me last reported for this server.

        **Not a credential, and it authenticates nothing.** It is the server's
        opaque public id for the caller -- the same value it puts in `owner` on
        every job object it returns.

        Persisted because it is the one thing here that CANNOT be fetched when
        it is needed. `GET /v1/me` answers *who you are now*, and the question
        this answers is *who did this server say I was last time* -- which the
        server has no record of, because it does not know the old principal was
        the same machine. Five things replace the principal without anyone doing
        anything wrong: a reimage, a rebuilt container, a CI image, a changed
        uid, and a client release that moves the derivation salt. All five look
        identical to "every job I ever ran has been deleted", and they have very
        different next steps.
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

    def key(self):
        '''This machine's private key, generated on first use.

        Generated locally and never sent anywhere. An operator generating one
        for a user is refused outright: the private half staying private is the
        single property DPoP has, and it is what holds the plaintext carve-out
        up.
        '''
        if self._key is not None:
            return self._key

        if self.key_path.exists():
            self._key = dpop.load_key(self.key_path.read_bytes())
            return self._key

        self._key = dpop.generate_key()
        _write_private(self.key_path, dpop.serialize_key(self._key))
        return self._key

    @property
    def thumbprint(self) -> str:
        '''The `jkt` the server knows this machine by.'''
        return dpop.jwk_thumbprint(dpop.public_jwk(self.key()))

    ######################################################################
    # Writing
    ######################################################################

    def update(self, **values) -> None:
        for name, value in values.items():
            if value is None:
                self._values.pop(name, None)
            else:
                self._values[name] = value
        self.save()

    def save_tokens(self, body: Dict[str, Any]) -> None:
        '''Persist the half of a session that outlives this command.

        The refresh token only. The access token stays in memory, and
        `access_token=None` is passed so that a file written by a client which
        stored one has it removed the first time this is called.
        '''
        self.update(access_token=None,
                    refresh_token=body.get("refresh_token"))

    def forget_tokens(self) -> None:
        self.update(access_token=None, refresh_token=None)

    def save(self) -> None:
        self._values.setdefault("directory_whitelist", [])
        _write_private(self.path,
                       (json.dumps(self._values, indent=2) + "\n").encode("utf-8"))


def _write_private(path: Path, payload: bytes) -> None:
    '''Write a file only this user can read, and tighten one that is wider.

    Opened with the mode rather than chmod'ed afterwards, so the contents are
    never briefly readable by anyone else. An existing file is re-tightened,
    because re-running configure over a file somebody widened has to fix it.
    '''
    path.parent.mkdir(parents=True, exist_ok=True)

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(path), flags, _PRIVATE)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)

    if sys.platform != "win32":
        # O_CREAT's mode applies only when the file is created, so an existing
        # 0644 file keeps its mode without this.
        if stat.S_IMODE(os.stat(path).st_mode) != _PRIVATE:
            os.chmod(path, _PRIVATE)
