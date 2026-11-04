'''
Where uploads and a job's artifacts live, and the signatures that let a client
write or read them.

Each signed URL is a route on this host. Its signature is that route's only
credential: it names one object and an expiry.
'''

import base64
import hashlib
import hmac
import os

from pathlib import Path

__all__ = ["Storage"]


_CHUNK = 1024 * 1024


class Storage:
    def __init__(self, datadir):
        self.uploads = Path(datadir) / "uploads"
        self.uploads.mkdir(parents=True, exist_ok=True)
        self.artifacts = Path(datadir) / "artifacts"

        secret = Path(datadir) / "secret"
        if not secret.exists():
            fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(os.urandom(32))
        self._key = secret.read_bytes()

    def upload_path(self, job_id: str) -> Path:
        return self.uploads / job_id

    def artifact_dir(self, job_id: str) -> Path:
        return self.artifacts / job_id

    def sign(self, *parts) -> str:
        mac = hmac.new(self._key, "\n".join(map(str, parts)).encode(), hashlib.sha256)
        # Unpadded: this goes in a query string.
        return base64.urlsafe_b64encode(mac.digest()).decode().rstrip("=")

    def verify(self, signature: str, *parts) -> bool:
        return hmac.compare_digest(self.sign(*parts), signature or "")

    def receive(self, job_id: str, stream, size: int) -> str:
        '''Write one upload of exactly ``size`` bytes, counting what arrives:
        ``Content-Length`` is only the sender's claim. More raises OverflowError,
        fewer ValueError. Returns its digest, taken on the way in so the upload
        is never read again for it.'''
        path = self.upload_path(job_id)
        # Renamed into place, so a half-received upload never looks complete.
        partial = path.with_name(path.name + ".part")
        digest = hashlib.sha256()
        written = 0
        try:
            with open(partial, "wb") as f:
                while True:
                    chunk = stream.read(_CHUNK)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > size:
                        raise OverflowError(f"the upload is past the {size} bytes it was granted")
                    digest.update(chunk)
                    f.write(chunk)
            if written != size:
                raise ValueError(f"the upload is {written} bytes and was granted {size}")
            os.replace(partial, path)
        finally:
            partial.unlink(missing_ok=True)
        return f"sha256:{digest.hexdigest()}"

    def discard(self, job_id: str) -> None:
        self.upload_path(job_id).unlink(missing_ok=True)
