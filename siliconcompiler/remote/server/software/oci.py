'''
Deriving an image in a registry: the base, with one layer on top.

A job's Python packages are built into a derived image (implementation-notes
§L): the image a node resolved to with the job's packages in a layer of their
own.
This is how that image comes to exist without pulling the base. The base's
layers are already in the registry, so the derived image is its manifest and
config with one layer appended, and only three small blobs move -- the layer,
the new config and the new manifest -- where copying the base down to add a
layer would move gigabytes for a tool image.

🔴 **In the base's own repository**, so every layer the new manifest names is
one the registry already holds there: a manifest may only reference blobs its
repository has.

⚠️ The registry is spoken to without credentials -- this server's own, on the
cluster's network, as `bootstrap` pushes to it -- and over plain HTTP where
`registries.conf` marks it insecure, as skopeo would.
'''

import gzip
import hashlib
import io
import json
import os
import tarfile
import time

from pathlib import Path
from typing import Tuple

__all__ = ["derive", "layer_from", "split_ref"]


_MANIFESTS = ("application/vnd.oci.image.manifest.v1+json",
              "application/vnd.docker.distribution.manifest.v2+json")
_LAYER_TYPES = {
    "application/vnd.oci.image.manifest.v1+json":
        "application/vnd.oci.image.layer.v1.tar+gzip",
    "application/vnd.docker.distribution.manifest.v2+json":
        "application/vnd.docker.image.rootfs.diff.tar.gzip",
}
_CONFIGS = {
    "application/vnd.oci.image.manifest.v1+json":
        "application/vnd.oci.image.config.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json":
        "application/vnd.docker.container.image.v1+json",
}
_REGISTRIES_CONF = ("/etc/containers/registries.conf",)
_TIMEOUT = 120


def split_ref(ref: str) -> Tuple[str, str, str]:
    '''`registry:5000/sc-tools@sha256:...` as (host, repository, reference),
    read as docker reads a reference: an unqualified name is Docker Hub's.'''
    from docker.auth import resolve_repository_name
    from docker.errors import InvalidRepository
    from docker.utils import parse_repository_tag

    repository, reference = parse_repository_tag(ref)
    # `repo:tag@digest` keeps its tag on the repository; the digest names it.
    repository = parse_repository_tag(repository)[0]
    try:
        host, repository = resolve_repository_name(repository)
    except InvalidRepository as e:
        raise ValueError(f"{ref} is not host/repository@digest: {e}") from None
    if not reference:
        raise ValueError(f"{ref} is not host/repository@digest")
    return host, repository, reference


def layer_from(directory: Path, inside: str) -> Tuple[bytes, str, str]:
    '''``directory`` as a gzipped layer that puts it at ``inside`` in the image.
    Returns (bytes, digest of the gzip, digest of the tar -- the diff id).

    Reproducible for the same tree: sorted, and no times or owners of this
    machine's, so the same packages make the same layer.
    '''
    tarred = io.BytesIO()
    with tarfile.open(fileobj=tarred, mode="w", format=tarfile.PAX_FORMAT) as tar:
        parts = [part for part in inside.strip("/").split("/") if part]
        for depth in range(1, len(parts)):
            info = tarfile.TarInfo("/".join(parts[:depth]))
            info.type, info.mode = tarfile.DIRTYPE, 0o755
            tar.addfile(info)
        for path in sorted([Path(directory)] + sorted(Path(directory).rglob("*"))):
            relative = path.relative_to(directory).as_posix()
            name = "/".join(parts) + ("" if relative == "." else f"/{relative}")
            if path.is_symlink():
                info = tarfile.TarInfo(name)
                info.type, info.linkname = tarfile.SYMTYPE, os.readlink(path)
                info.mode = 0o777
                tar.addfile(info)
            elif path.is_dir():
                info = tarfile.TarInfo(name)
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
            elif path.is_file():
                info = tarfile.TarInfo(name)
                info.size = path.stat().st_size
                info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
                with open(path, "rb") as handle:
                    tar.addfile(info, handle)
    raw = tarred.getvalue()
    zipped = gzip.compress(raw, mtime=0)
    return zipped, _digest(zipped), _digest(raw)


def derive(base_ref: str, layer: Tuple[bytes, str, str], comment: str) -> Tuple[str, str]:
    '''Push the base with ``layer`` on top into the base's own repository, by
    digest. Returns (``host/repository@digest``, digest).

    🔴 **By digest, with no tag** (profile D39): nothing names a derived image
    but its content, so nothing can be pointed at other content later. ⚠️ A
    registry garbage collection that deletes untagged manifests would take
    them; this stack's registry runs none.'''
    import requests

    host, repository, reference = split_ref(base_ref)
    root = f"{_scheme(host)}://{host}/v2/{repository}"
    session = requests.Session()

    got = session.get(f"{root}/manifests/{reference}",
                      headers={"Accept": ", ".join(_MANIFESTS)}, timeout=_TIMEOUT)
    got.raise_for_status()
    manifest = got.json()
    kind = manifest.get("mediaType") or got.headers.get("Content-Type", "").split(";")[0]
    if kind not in _MANIFESTS:
        raise RuntimeError(f"{base_ref} is a {kind or 'manifest of no type'}, not one "
                           "image: a multi-platform index cannot take a layer")

    config = session.get(f"{root}/blobs/{manifest['config']['digest']}", timeout=_TIMEOUT)
    config.raise_for_status()
    config = config.json()

    data, digest, diff_id = layer
    _upload(session, root, data, digest)

    config.setdefault("rootfs", {"type": "layers", "diff_ids": []})["diff_ids"].append(diff_id)
    config.setdefault("history", []).append({
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "created_by": "sc-server", "comment": comment})
    config_bytes = json.dumps(config, separators=(",", ":")).encode()
    config_digest = _digest(config_bytes)
    _upload(session, root, config_bytes, config_digest)

    manifest["config"] = {"mediaType": _CONFIGS[kind], "digest": config_digest,
                          "size": len(config_bytes)}
    manifest["layers"] = list(manifest.get("layers") or []) + [
        {"mediaType": _LAYER_TYPES[kind], "digest": digest, "size": len(data)}]
    manifest["mediaType"] = kind
    body = json.dumps(manifest, separators=(",", ":")).encode()
    derived = _digest(body)
    put = session.put(f"{root}/manifests/{derived}", data=body,
                      headers={"Content-Type": kind}, timeout=_TIMEOUT)
    put.raise_for_status()
    return f"{host}/{repository}@{derived}", derived


def _upload(session, root: str, data: bytes, digest: str) -> None:
    if session.head(f"{root}/blobs/{digest}", timeout=_TIMEOUT).status_code == 200:
        return
    started = session.post(f"{root}/blobs/uploads/", timeout=_TIMEOUT)
    started.raise_for_status()
    location = started.headers["Location"]
    if location.startswith("/"):
        location = root.split("/v2/", 1)[0] + location
    joiner = "&" if "?" in location else "?"
    done = session.put(f"{location}{joiner}digest={digest}", data=data,
                       headers={"Content-Type": "application/octet-stream"},
                       timeout=_TIMEOUT)
    done.raise_for_status()


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _scheme(host: str, confs=_REGISTRIES_CONF) -> str:
    '''http where registries.conf marks the registry insecure, as skopeo reads
    it; https otherwise. Read as TOML, so a commented-out key, a mirror's own
    `insecure` and either quoting all read as skopeo reads them.'''
    from siliconcompiler.utils import tomllib

    for conf in [os.environ.get("CONTAINERS_REGISTRIES_CONF"), *confs]:
        if not conf or not os.path.isfile(conf):
            continue
        try:
            with open(conf, "rb") as f:
                registries = tomllib.load(f).get("registry") or []
        except (OSError, ValueError):
            continue
        for entry in registries:
            if isinstance(entry, dict) and entry.get("location") == host \
                    and entry.get("insecure") is True:
                return "http"
    return "https"
