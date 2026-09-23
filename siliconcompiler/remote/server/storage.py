'''
Where the bytes live, and how a client is let at them.

The contract says an upload goes to a presigned ``PUT`` and never through the
API process. That is a shape rather than a vendor: ``storage_locations.uri_base``
is a URI, so ``file://`` is a first-class deployment and the "presigned" URL is a
signed route on this host. Every other deployment swaps this module and nothing
above it changes.

The signature is the credential on that route -- no ``Authorization`` header, no
DPoP proof -- because that is what a presigned URL is. What bounds it is that it
names one job, expires, and binds the byte count the grant was issued for.
'''

import base64
import hashlib
import hmac
import os
import shutil

from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlsplit, unquote

__all__ = ["Storage", "SignatureError"]


# A grant is short-lived on purpose: it is re-issuable, so a client whose upload
# was interrupted asks for another rather than holding one open.
GRANT_SECONDS = 900

# How long an artifact link stands up. Much shorter than an upload grant,
# because nothing has to be prepared before it is used: the client is redirected
# to it and follows it in the same breath.
DOWNLOAD_SECONDS = 300

_CHUNK = 1024 * 1024


class SignatureError(Exception):
    '''The signed URL does not check out: expired, altered or never ours.'''


class Storage:
    '''One deployment's object store, over a local directory.

    Two trees, and they are deliberately separate. ``uploads/`` holds what a
    client PUT and nothing has yet looked at; ``artifacts/`` holds what a run
    produced. An upload is not an artifact until it has been through
    :mod:`~siliconcompiler.remote.server.archive`, and mixing them would put
    unexamined bytes in the tree that gets served back out.
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

        # Derived rather than reused. It is the same secret file the tokens are
        # signed with -- one key for an operator to protect -- but a signature
        # over a URL and a signature over a token must not be interchangeable,
        # and a keyed derivation is what stops one being presented as the other.
        self._key = hashlib.blake2b(secret, person=b"sc-storage", digest_size=32).digest()

    ######################################################################
    # Uploads
    ######################################################################

    def upload_path(self, job_id: str) -> Path:
        '''Where one job's staged archive is, whether or not it is there yet.'''
        return self.uploads / job_id

    def sign_upload(self, job_id: str, max_bytes: int, expires_at: int) -> str:
        '''The capability half of the grant.

        ``max_bytes`` is signed rather than merely published: the grant is
        re-issuable, and a re-issue that could widen the byte count would make
        `limits.max_upload_bytes` advisory.
        '''
        return self._sign(f"upload\n{job_id}\n{max_bytes}\n{expires_at}")

    def verify_upload(self, job_id: str, max_bytes: str, expires_at: str,
                      signature: str, when: float) -> int:
        '''Check a presented signature, and return the byte ceiling it carries.'''
        try:
            ceiling = int(max_bytes)
            deadline = int(expires_at)
        except (TypeError, ValueError):
            raise SignatureError("malformed grant") from None

        expected = self._sign(f"upload\n{job_id}\n{ceiling}\n{deadline}")
        if not hmac.compare_digest(expected, signature or ""):
            raise SignatureError("the signature does not match this URL")

        # Checked after the signature, deliberately: an expiry read off an
        # unverified URL is a number the caller chose.
        if when > deadline:
            raise SignatureError("this upload grant has expired")

        return ceiling

    def receive(self, job_id: str, stream, ceiling: int) -> Tuple[int, str]:
        '''Write one upload, counting as it goes.

        The count is enforced here rather than from ``Content-Length``, which is
        a claim the sender makes about a body it is still sending.
        '''
        path = self.upload_path(job_id)
        digest = hashlib.sha256()
        written = 0

        # Written under a temporary name and renamed, so a half-received upload
        # is never mistaken for a complete one by anything that only checks
        # whether the file is there.
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
        '''What storage reports about a staged upload, or None if there is none.

        Re-read from the object rather than remembered from the PUT. The digest
        submit compares against has to describe the bytes that are on disk now,
        or the comparison is between two things the client said.
        '''
        path = self.upload_path(job_id)
        if not path.is_file():
            return None

        digest = hashlib.sha256()
        size = 0
        with open(path, "rb") as f:
            while True:
                chunk = f.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)

        return size, f"sha256:{digest.hexdigest()}"

    def discard_upload(self, job_id: str) -> None:
        '''Drop a staged upload. Not an error if it was never there.'''
        self.upload_path(job_id).unlink(missing_ok=True)
        self.upload_path(job_id).with_name(job_id + ".part").unlink(missing_ok=True)

    ######################################################################
    # Artifacts
    ######################################################################

    def artifact_dir(self, job_id: str) -> Path:
        return self.artifacts / job_id

    def artifact_path(self, storage_key: str) -> Path:
        '''Where one artifact's bytes are.

        The key is the server's own, never the client's, and it is resolved
        against the artifact root and checked -- a storage layer that joins a
        stored string onto a path without looking is one schema change away
        from serving whatever that string says.
        '''
        resolved = (self.artifacts / storage_key).resolve()
        root = self.artifacts.resolve()
        if root not in resolved.parents:
            raise SignatureError(f"{storage_key} is not inside this store")
        return resolved

    def sign_download(self, artifact_id: str, expires_at: int) -> str:
        '''The capability half of an artifact handover.

        A different message prefix from an upload's, so a grant to PUT one job's
        archive can never be presented as a grant to GET another job's outputs.
        '''
        return self._sign(f"download\n{artifact_id}\n{expires_at}")

    def verify_download(self, artifact_id: str, expires_at: str,
                        signature: str, when: float) -> None:
        try:
            deadline = int(expires_at)
        except (TypeError, ValueError):
            raise SignatureError("malformed link") from None

        expected = self._sign(f"download\n{artifact_id}\n{deadline}")
        if not hmac.compare_digest(expected, signature or ""):
            raise SignatureError("the signature does not match this URL")
        if when > deadline:
            raise SignatureError("this link has expired")

    def discard_artifacts(self, job_id: str) -> None:
        shutil.rmtree(self.artifact_dir(job_id), ignore_errors=True)

    ######################################################################

    def _sign(self, message: str) -> str:
        mac = hmac.new(self._key, message.encode(), hashlib.sha256).digest()
        # urlsafe and unpadded: this goes in a query string.
        return base64.urlsafe_b64encode(mac).decode().rstrip("=")
