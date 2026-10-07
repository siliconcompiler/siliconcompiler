'''
Which principal this machine is, to a server that does not verify the answer.

The identity is derived from `(machine, uid)`: machine alone would merge every
user on a login node. The uid, not the username, so a rename keeps the identity.
'''

import hashlib
import os
import platform
import subprocess

from pathlib import Path
from typing import Optional, Tuple

__all__ = ["machine_fingerprint", "local_subject", "display_name"]


# Changing this silently migrates every derived identity at once.
_SALT = b"siliconcompiler.remote.v1"


def machine_fingerprint() -> Tuple[Optional[str], str]:
    '''``(machine id, source)``; ``(None, "none")`` rather than an invented id.'''
    system = platform.system()

    if system == "Linux":
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            value = _read(Path(path))
            if value:
                return value, "linux_machine_id"
        return None, "none"

    if system == "Darwin":
        value = _ioreg_platform_uuid()
        return (value, "macos_platform_uuid") if value else (None, "none")

    if system == "Windows":
        value = _windows_machine_guid()
        return (value, "windows_machine_guid") if value else (None, "none")

    return None, "none"


def _read(path: Path) -> Optional[str]:
    try:
        value = path.read_text().strip()
    except OSError:
        return None
    return value or None


def _ioreg_platform_uuid() -> Optional[str]:
    try:
        output = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None

    for line in output.splitlines():
        if "IOPlatformUUID" in line:
            _, _, value = line.partition("=")
            return value.strip().strip('"') or None
    return None


def _windows_machine_guid() -> Optional[str]:
    try:
        import winreg
    except ImportError:                                          # pragma: no cover
        return None

    try:                                                         # pragma: no cover
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Cryptography") as handle:
            value, _ = winreg.QueryValueEx(handle, "MachineGuid")
        return value or None
    except OSError:
        return None


def _uid() -> str:
    '''The numeric uid, or on Windows, which has none, the username.'''
    getuid = getattr(os, "getuid", None)
    if getuid is not None:
        return str(getuid())
    return os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"


def local_subject() -> Tuple[str, Optional[str], str]:
    '''``(subject, machine_id_hash, machine_id_source)`` for `client_id=local:<subject>`.

    The subject is the unique identity key; the hash is only a device label, and
    deliberately not unique.
    '''
    machine, source = machine_fingerprint()
    uid = _uid()

    derived = hashlib.sha256()
    derived.update(_SALT)
    derived.update(b"\0")
    derived.update((machine or "unknown-machine").encode("utf-8"))
    derived.update(b"\0")
    derived.update(uid.encode("utf-8"))

    subject = f"{derived.hexdigest()[:32]}:{uid}"

    label = None
    if machine:
        label = hashlib.sha256(_SALT + b"\0" + machine.encode("utf-8")).hexdigest()[:32]

    return subject, label, source


def display_name() -> str:
    '''The username, for display only: the subject is derived from the uid, so
    nothing is keyed on it.'''
    import getpass

    try:
        return getpass.getuser()
    except Exception:                                            # noqa: BLE001
        return "unknown"
