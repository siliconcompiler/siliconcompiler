'''
Where the bytes live, and how a client is let at them.

``storage_locations.uri_base`` is a URI, so ``file://`` is a first-class
deployment and the contract's presigned ``PUT`` is a signed route on this host;
another backend swaps this module alone. The signature is that route's only
credential, bounded by naming one job, expiring and binding the byte count.
'''

import base64
import hashlib
import hmac
import os

from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlsplit, unquote

__all__ = ["Storage", "SignatureError"]


# Short-lived on purpose: it is re-issuable, so an interrupted client asks again.
GRANT_SECONDS = 900

# 🔴 What a grant must outlast (surface §14): the upload is one PUT with no
# resume, so the largest upload over a slow link, about fifteen minutes a GiB.
GRANT_BITS_PER_SECOND = 10_000_000


def grant_seconds(max_upload_bytes: int) -> int:
    '''How long an upload grant lives, for a deployment accepting this much.'''
    return max(GRANT_SECONDS, -(-int(max_upload_bytes) * 8 // GRANT_BITS_PER_SECOND))


# Much shorter than an upload grant: the client follows the redirect at once.
DOWNLOAD_SECONDS = 300

_CHUNK = 1024 * 1024


class SignatureError(Exception):
    '''The signed URL does not check out: expired, altered or never ours.'''


class Storage:
    '''One deployment's object store, over a local directory.

    ``uploads/`` and ``artifacts/`` are deliberately separate trees: an upload
    is unexamined until :mod:`~siliconcompiler.remote.server.staging.archive`
    has seen it, and must never be in the tree that gets served.
    '''

    def __init__(self, datadir, uri_base: str, secret: bytes):
        self.datadir = Path(datadir)

        parts = urlsplit(uri_base)
        if parts.scheme != "file":
            raise ValueError(
                f"this server implements file:// storage and was given {uri_base}; "
                "another scheme needs its own Storage")
        self.artifacts = Path(unquote(parts.path))
        self.uploads = self.datadir / "uploads"

        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.uploads.mkdir(parents=True, exist_ok=True)

        # Derived, not reused: one secret for the operator, but a URL's
        # signature must never pass as a token's.
        self._key = hashlib.blake2b(secret, person=b"sc-storage", digest_size=32).digest()

    def upload_path(self, job_id: str) -> Path:
        '''Where one job's staged archive is, whether or not it is there yet.'''
        return self.uploads / job_id

    def sign_upload(self, job_id: str, max_bytes: int, expires_at: int) -> str:
        '''The capability half of the grant. ``max_bytes`` is signed, so a
        re-issue cannot widen `limits.max_upload_bytes`.'''
        return self._sign(f"upload\n{job_id}\n{max_bytes}\n{expires_at}")

    def verify_upload(self, job_id: str, max_bytes: str, expires_at: str,
                      signature: str, when: float) -> int:
        '''Check a presented signature, and return the byte ceiling it carries.'''
        try:
            ceiling = int(max_bytes)
        except (TypeError, ValueError):
            raise SignatureError("malformed grant") from None
        self._verify(lambda deadline: f"upload\n{job_id}\n{ceiling}\n{deadline}",
                     expires_at, signature, when, "this upload grant has expired",
                     malformed="malformed grant")
        return ceiling

    def receive(self, job_id: str, stream, ceiling: int) -> Tuple[int, str]:
        '''Write one upload, counting as it goes: ``Content-Length`` is only the
        sender's claim.'''
        path = self.upload_path(job_id)
        digest = hashlib.sha256()
        written = 0

        # Renamed into place, so a half-received upload never looks complete.
        partial = path.with_name(path.name + ".part")
        try:
            with open(partial, "wb") as f:
                while True:
                    chunk = stream.read(_CHUNK)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > ceiling:
                        raise ValueError(
                            f"the upload exceeds the {ceiling} bytes this grant allows")
                    digest.update(chunk)
                    f.write(chunk)
            os.replace(partial, path)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise

        return written, f"sha256:{digest.hexdigest()}"

    def stat_upload(self, job_id: str) -> Optional[Tuple[int, str]]:
        '''What storage reports about a staged upload, or None. Re-read from
        disk, so submit never compares two things the client said.'''
        path = self.upload_path(job_id)
        if not path.is_file():
            return None

        from siliconcompiler.utils import file_digest

        return path.stat().st_size, f"sha256:{file_digest(path).hexdigest()}"

    def discard_upload(self, job_id: str) -> None:
        '''Drop a staged upload. Not an error if it was never there.'''
        self.upload_path(job_id).unlink(missing_ok=True)
        self.upload_path(job_id).with_name(job_id + ".part").unlink(missing_ok=True)

    def artifact_dir(self, job_id: str) -> Path:
        return self.artifacts / job_id

    def artifact_path(self, storage_key: str) -> Path:
        '''Where one artifact's bytes are; the key is the server's own, and is
        still confined to the artifact root.'''
        resolved = (self.artifacts / storage_key).resolve()
        root = self.artifacts.resolve()
        if root not in resolved.parents:
            raise SignatureError(f"{storage_key} is not inside this store")
        return resolved

    def sign_download(self, artifact_id: str, expires_at: int) -> str:
        '''The capability half of an artifact handover. Each grant has its own
        prefix, so none can be presented as another.'''
        return self._sign(f"download\n{artifact_id}\n{expires_at}")

    def sign_stream(self, job_id: str, step: str, index: str,
                    expires_at: int, nonce: str = "") -> str:
        '''The capability half of a live tail.'''
        # The nonce makes every URL distinct, so each serves one connection.
        return self._sign(f"stream\n{job_id}\n{step}\n{index}\n{expires_at}\n{nonce}")

    def verify_stream(self, job_id: str, step: str, index: str,
                      expires_at: str, signature: str, when: float,
                      nonce: Optional[str] = "") -> None:
        self._verify(
            lambda deadline: f"stream\n{job_id}\n{step}\n{index}\n{deadline}\n{nonce or ''}",
            expires_at, signature, when, "this stream link has expired")

    def sign_job_stream(self, job_id: str, expires_at: int, nonce: str = "") -> str:
        '''The capability half of a whole job's live stream; its own prefix, not
        the node form with empty coordinates.'''
        return self._sign(f"stream-job\n{job_id}\n{expires_at}\n{nonce}")

    def verify_job_stream(self, job_id: str, expires_at: str, signature: str,
                          when: float, nonce: Optional[str] = "") -> None:
        self._verify(lambda deadline: f"stream-job\n{job_id}\n{deadline}\n{nonce or ''}",
                     expires_at, signature, when, "this stream link has expired")

    def verify_download(self, artifact_id: str, expires_at: str,
                        signature: str, when: float) -> None:
        self._verify(lambda deadline: f"download\n{artifact_id}\n{deadline}",
                     expires_at, signature, when, "this link has expired")

    def _verify(self, message, expires_at, signature, when: float, expired: str,
                malformed: str = "malformed link") -> None:
        '''One presented signature against the message ``message(deadline)``
        signs, then its deadline -- checked after the signature, deliberately:
        an expiry read off an unverified URL is a number the caller chose.'''
        try:
            deadline = int(expires_at)
        except (TypeError, ValueError):
            raise SignatureError(malformed) from None
        if not hmac.compare_digest(self._sign(message(deadline)), signature or ""):
            raise SignatureError("the signature does not match this URL")
        if when > deadline:
            raise SignatureError(expired)

    def _sign(self, message: str) -> str:
        mac = hmac.new(self._key, message.encode(), hashlib.sha256).digest()
        # urlsafe and unpadded: this goes in a query string.
        return base64.urlsafe_b64encode(mac).decode().rstrip("=")
