'''
Which principal this machine is, to a server that does not verify the answer.

The identity is `(machine, uid)`, derived rather than configured. The objection
it answers is multi-user-on-one-machine, which is the common case here: a
machine-only key would collapse every user on a login node into one identity,
and B could cancel A's jobs.

Derive from the uid and display the username. The uid survives a rename and is
stable across a cluster; deriving from the username would make a rename a new
identity.
'''

import hashlib
import os
import platform
import subprocess

from pathlib import Path
from typing import Optional, Tuple

__all__ = ["machine_fingerprint", "local_subject", "display_name"]


# Changing this changes every derived subject at once -- a silent, uncoordinated
# identity migration for every unauthenticated deployment. It is a constant so
# that a change to it is a visible edit rather than a side effect.
_SALT = b"siliconcompiler.remote.v1"


def machine_fingerprint() -> Tuple[Optional[str], str]:
    '''This machine's id, and which source produced it.

    Returns `(value, source)` where source is one of the four the schema
    accepts. There is no persisted fallback: a machine that cannot answer says
    so with `none` rather than inventing an id that would move on its own.
    '''
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
    '''The numeric uid, or the username where there is no uid.

    Windows has no uid; the login name is the closest stable thing, and a
    deployment mixing the two is already two identities per person.
    '''
    getuid = getattr(os, "getuid", None)
    if getuid is not None:
        return str(getuid())
    return os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"


def local_subject() -> Tuple[str, Optional[str], str]:
    '''The `client_id=local:<derivation>` value, and the fingerprint beside it.

    Returns `(subject, machine_id_hash, machine_id_source)`. The uid goes into
    the derivation rather than being concatenated after it, which is the same
    operation a per-application machine id already is with one more input.

    The hash is a separate value from the subject on purpose: the subject is the
    identity key and is unique, while `devices.machine_id_hash` is a label and
    is deliberately not.
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
    '''What a person recognises, which is never a number.

    Goes in `users.display_name` and in the device's name; nothing is keyed on
    it, so a rename costs nothing.
    '''
    import getpass

    try:
        user = getpass.getuser()
    except Exception:                                            # noqa: BLE001
        user = "unknown"

    return f"{user}@{platform.node() or 'unknown'}"
