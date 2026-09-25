'''
What owns each file a job names, and where the file came from.

Both ends ask this. The client asks it to decide what goes in the archive; the
server asks it to decide whether a PDK, library or FPGA device the flow needs is
one it holds or one whose files had to arrive -- and refuses the job at
re-derivation, rather than on its first node, when neither is true.

🔴 **The line is drawn by what owns a file, and no flag is consulted.**
`copy=True` is opt-in and per parameter, so a job whose sources had not been
marked went up as references to somebody else's filesystem. Every file has an
owner that SiliconCompiler already records: the design, every PDK, standard-cell
library and FPGA device are objects under ``library.<name>``, and a tool's
scripts sit under ``tool.<name>``.

=====================  ==========================================
The file belongs to    It is uploaded
=====================  ==========================================
the user's design      always
a PDK, library, FPGA   only when its source is local or editable
a tool                 only when its source is local or editable
=====================  ==========================================

🔴 **"Local" is the dataroot's registered SOURCE, never where the file is
now.** Every resolved file is on local disk -- a lambdapdk PDK is fetched into
the cache on first use -- so judging by location would upload every PDK in
every job, which is the exact opposite of the rule, and it would do it
silently.
'''

import os
import re

from typing import List, Optional, Tuple

__all__ = ["DESIGN", "PROJECT", "RESOURCE_KINDS", "LOCAL", "EDITABLE",
           "INSTALLED", "REMOTE", "ENVIRONMENT", "owner", "source", "uploads",
           "holding", "env_names"]


# Who a file belongs to, when it is neither a resource nor a tool.
DESIGN = "design"
PROJECT = "project"

# The resource kinds whose files follow the local-or-editable rule -- the same
# words the contract's `resource_kinds` uses.
RESOURCE_KINDS = ("pdk", "library", "fpga")

# Where a dataroot's files come from.
LOCAL = "local"            # a path on this machine, or no dataroot at all
EDITABLE = "editable"      # a Python package installed editable
INSTALLED = "installed"    # a Python package installed normally
REMOTE = "remote"          # git, https, or anything fetched -- cached or not
# 🔴 Rooted in an environment variable -- `$FOUNDRY_ROOT/...` -- which names a
# location that differs by SITE. That is why SiliconCompiler documents it for
# proprietary PDKs, and uploading one defeats the indirection: neither local
# nor editable (D109). Told from the registered source, which keeps the
# variable unexpanded; SiliconCompiler expands it only at resolution.
ENVIRONMENT = "environment"

_ENV_NAME = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")

# Parameters that are paths and are never the run's input. The build and cache
# directories are this machine's; the credentials file is this machine's KEY.
_NEVER = {("option", "builddir"), ("option", "cachedir"),
          ("option", "credentials")}


def owner(project, key) -> Tuple[str, Optional[str]]:
    '''``(kind, name)`` for the object a parameter belongs to.

    ``kind`` is one of `RESOURCE_KINDS`, ``"tool"``, `DESIGN` or `PROJECT`.

    ⚠️ The resource classes are tested BEFORE `Design`, because `PDK` and
    `StdCellLibrary` subclass it -- tested the other way round, every PDK would
    be the user's design and always uploaded.
    '''
    if key[0] == "library" and len(key) > 1:
        from siliconcompiler import FPGADevice, PDK, StdCellLibrary

        obj = project.get("library", key[1], field="schema")
        if isinstance(obj, PDK):
            return "pdk", key[1]
        if isinstance(obj, FPGADevice):
            return "fpga", key[1]
        if isinstance(obj, StdCellLibrary):
            return "library", key[1]
        return DESIGN, key[1]

    if key[0] == "tool" and len(key) > 1:
        return "tool", key[1]

    return PROJECT, None


def env_names(path) -> List[str]:
    '''The environment variables a registered path is rooted in.'''
    return _ENV_NAME.findall(str(path or ""))


def source(resolvers, dataroot: Optional[str], _seen=None,
           path: Optional[str] = None) -> str:
    '''Where files under ``dataroot`` come from, judged by how it was
    REGISTERED. ``resolvers`` is the owning schema's
    ``_find_files_dataroot_resolvers(True)``.

    A dataroot that names another dataroot is judged by the one it names; a
    keypath dataroot, by nothing it can be traced to, is local -- the cautious
    answer, since it means sending the file rather than trusting the server
    has it.
    '''
    from siliconcompiler.package import (
        DatarootResolver, FileResolver, KeyPathResolver, PythonPathResolver,
        RemoteResolver)

    if not dataroot:
        # A path with no dataroot is judged by itself.
        return ENVIRONMENT if env_names(path) else LOCAL

    resolver = resolvers.get(dataroot)
    if resolver is None:
        return LOCAL

    if isinstance(resolver, RemoteResolver):
        return REMOTE
    if isinstance(resolver, PythonPathResolver):
        module = resolver.urlpath
        return EDITABLE if PythonPathResolver.is_python_module_editable(module) \
            else INSTALLED
    if isinstance(resolver, DatarootResolver):
        seen = set(_seen or ())
        if dataroot in seen:
            return LOCAL
        seen.add(dataroot)
        return source(resolvers, resolver.urlpath, seen)
    if isinstance(resolver, FileResolver):
        # ⚠️ `source`, never `urlpath`: `urlpath` has already expanded the
        # variable -- with the job's `option,env` laid over the environment.
        return ENVIRONMENT if env_names(_registered(resolver)) else LOCAL
    if isinstance(resolver, KeyPathResolver):
        return LOCAL
    # Something this client does not know. Sending it is the answer that
    # cannot leave a job short of a file.
    return LOCAL


def uploads(project, key, dataroot: Optional[str], resolvers,
            path: Optional[str] = None) -> bool:
    '''Whether one value of one parameter goes in the archive.'''
    if tuple(key[:2]) in _NEVER:
        return False

    kind, _ = owner(project, key)
    if kind in (DESIGN, PROJECT):
        return True

    return source(resolvers, dataroot, path=path) in (LOCAL, EDITABLE)


def holding(project, name: str, collection_dir) -> Tuple[bool, bool]:
    '''Whether this server can supply every file of ``library.<name>``, and
    whether it will use an uploaded copy for any of them.

    Returns ``(held, uploaded)``. A file is supplied when:

    - it arrived in the archive -- which SiliconCompiler resolves BEFORE the
      original path, so an upload wins over a copy the server also has;
    - its source is remote, which this server fetches on first use;
    - its source is an installed package this server can import;
    - its source is local and the path exists here too, as an env-var
      dataroot pointing at the server's own copy does.

    🔴 **Refuses only what it is sure of.** A local file that is neither in
    the archive nor on this machine is certainly missing; anything it cannot
    trace -- a keypath dataroot, a chain it cannot follow -- counts as
    supplied, because a false refusal stops a job that would have run, where
    a false pass is only the failure this check exists to move earlier.
    '''
    import importlib.util

    held, uploaded = True, False

    for key in sorted(project.allkeys("library", name, include_default=False)):
        full = ("library", name, *key)
        if len(full) > 4 and full[2] == "tool" and full[4] == "task":
            continue
        param = project.get(*full, field=None)
        if not param.is_path:
            continue

        resolvers = project.get(*full[:-1], field="schema") \
            ._find_files_dataroot_resolvers(True)

        for value, step, index in param.getvalues(return_values=False):
            for one in _each(value):
                if one.get() is None:
                    continue

                dataroot = one.get(field="dataroot")
                if _collected(one, collection_dir):
                    uploaded = True
                    continue

                kind = source(resolvers, dataroot, path=one.get())
                if kind == REMOTE:
                    continue
                if kind in (INSTALLED, EDITABLE):
                    module = resolvers[dataroot].urlpath
                    if importlib.util.find_spec(module) is None:
                        held = False
                    continue

                if not _present_here(one.get(), resolvers.get(dataroot)):
                    held = False

    return held, uploaded


def _each(value):
    from siliconcompiler.schema.parametervalue import NodeListValue, NodeSetValue

    if isinstance(value, (NodeSetValue, NodeListValue)):
        return value.values
    return [value]


def _collected(value, collection_dir) -> bool:
    if not collection_dir or not os.path.isdir(collection_dir):
        return False
    try:
        found = value.resolve_path(search=[], collection_dir=str(collection_dir))
    except FileNotFoundError:
        return False
    return bool(found) and str(found).startswith(str(collection_dir))


def _present_here(path: str, resolver) -> bool:
    '''Whether a local- or environment-sourced file is at its path on THIS
    machine.

    🔴 **Expanded with THIS process's environment and never the job's
    `option,env`**, which carries the CLIENT's value -- honouring it would
    expand to a path that exists only on the client's machine. See
    `runspec.normalize`, which drops those names from the run too.

    Unknowable is present: a dataroot that is not a plain path is traced no
    further here, per the rule above.
    '''
    from siliconcompiler.package import FileResolver

    if resolver is None:
        full = os.path.expandvars(path)
        # A relative path with no dataroot is relative to the caller's own
        # working directory, which is not here.
        return os.path.isabs(full) and os.path.exists(full)

    if not isinstance(resolver, FileResolver):
        return True

    # From the REGISTERED source, expanded here with os.environ alone.
    # `resolver.resolve()` would expand it with the job's `option,env`.
    root = os.path.expandvars(_registered(resolver))
    if "$" in root:
        # An env var this server does not set: the path it names is not here.
        return False
    if not os.path.isabs(root):
        return True
    return os.path.exists(os.path.join(root, os.path.expandvars(path)))


def _registered(resolver) -> str:
    '''A file resolver's source as registered, variables unexpanded.'''
    registered = str(getattr(resolver, "source", "") or "")
    return registered[7:] if registered.startswith("file://") else registered
