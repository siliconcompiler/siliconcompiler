# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
"""Enumerate the distinct parameterizations of a module in an elaborated design.

A hardened macro has no parameters, but the RTL that instantiates it does. To
harden a parameterized module we first need to know, across the whole design,
*which* concrete parameter combinations it is actually instantiated with, and
what its resolved port widths are for each of those combinations. This module
uses pyslang to elaborate a design and answer exactly that.

The output is a list of :class:`Parameterization` objects -- one per distinct
combination of parameter values -- each carrying the concrete parameter values,
the resolved (constant-width) port list, the hierarchical paths of the instances
that use it, and a sanitized, collision-free variant name suitable for use as a
module/macro/file name.

This is the analysis foundation for the wrapper + hardened-variant generation
flow; codegen and the alias wiring build on top of it.
"""

from __future__ import annotations

import hashlib
import re
import shlex
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from siliconcompiler.tools.slang import pyslang
from siliconcompiler.tools._common import distinct

if TYPE_CHECKING:
    from siliconcompiler import Design

# A concrete parameter value, as recovered from the elaborated design. ``bool``
# is handled distinctly from ``int`` by the type tagging and literal formatting.
ParamValue = Union[bool, int, float, str]
# A pyslang Compilation / symbol; typed loosely since pyslang has no stubs.
Compilation = Any


class UniquifyError(RuntimeError):
    """Raised when elaboration fails or the request cannot be satisfied."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class ParamPort:
    """A single resolved port of a parameterization.

    Attributes:
        name (str): Port name.
        direction (str): One of ``"input"``, ``"output"``, ``"inout"``,
            ``"ref"`` (or the lower-cased pyslang direction for anything else).
        width (int): Resolved bit width (>= 1), constant for this combination.
    """

    __slots__ = ("name", "direction", "width")

    def __init__(self, name: str, direction: str, width: int) -> None:
        self.name = name
        self.direction = direction
        self.width = width

    def __repr__(self) -> str:
        return f"ParamPort({self.name!r}, {self.direction!r}, {self.width})"

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, ParamPort) and self.name == other.name and
                self.direction == other.direction and self.width == other.width)


class Parameterization:
    """One distinct parameter combination of a module.

    Attributes:
        module (str): The (source) module name being uniquified.
        params (dict): Ordered mapping of parameter name -> concrete value
            (``int``, ``float`` or ``str``). Only overridable module parameters
            are included; localparams are excluded.
        ports (list): List of :class:`ParamPort`, in declaration order.
        instances (list): Hierarchical paths of instances using this
            combination (e.g. ``"top.u_hb16"``).
        name (str): Sanitized, collision-free variant name (assigned by
            :func:`enumerate_modules`).
    """

    def __init__(self, module: str, params: Dict[str, ParamValue],
                 ports: List[ParamPort]) -> None:
        self.module = module
        self.params = params
        self.ports = ports
        self.instances: List[str] = []
        self.name: str = ""

    @property
    def signature(self) -> Tuple[Tuple[str, str, str], ...]:
        """A stable, type-aware key that uniquely identifies this combination.

        The type tag distinguishes e.g. integer ``8`` from the string
        ``"8"`` so they never collapse into the same variant.

        Returns:
            tuple: ``(name, type_tag, value_text)`` triples, one per parameter.
        """
        return tuple((k, _type_tag(v), str(v)) for k, v in self.params.items())

    def __repr__(self) -> str:
        return (f"Parameterization(module={self.module!r}, name={self.name!r}, "
                f"params={self.params!r}, ports={self.ports!r}, "
                f"instances={self.instances!r})")


def _type_tag(value: ParamValue) -> str:
    if isinstance(value, bool):
        return "b"
    if isinstance(value, int):
        return "i"
    if isinstance(value, float):
        return "r"
    return "s"


# ---------------------------------------------------------------------------
# pyslang value / port extraction
# ---------------------------------------------------------------------------


def _sv_int_to_python(const_value: Any) -> int:
    """Convert a pyslang integral ConstantValue to a Python int.

    ``str()`` of an integral constant is either a plain decimal (``"16"``) or a
    sized SystemVerilog literal (``"40'h612f623a63"``, ``"32'sd-5"``), so both
    forms are parsed.

    Args:
        const_value: An integral pyslang ``ConstantValue``.

    Returns:
        int: The value as a native Python integer.

    Raises:
        UniquifyError: If the literal's base cannot be recognised.
    """
    text = str(const_value).strip()
    if "'" not in text:
        return int(text)

    _, rest = text.split("'", 1)
    rest = rest.lstrip("sS")  # drop signed marker if present
    base_char = rest[0].lower()
    digits = rest[1:].replace("_", "")
    base = {"b": 2, "o": 8, "d": 10, "h": 16}.get(base_char)
    if base is None:
        raise UniquifyError(f"cannot parse integer constant {text!r}")
    return int(digits, base)


def _param_value(param_symbol: Any) -> ParamValue:
    """Extract a Python value from a pyslang ParameterSymbol.

    A parameter declared ``string`` comes back as a Python ``str``; an integral
    parameter as a Python ``int``; a real as a ``float``. Note: an *untyped*
    parameter initialized with a string literal is integral in SystemVerilog and
    is therefore represented by its integer value.

    Args:
        param_symbol: A pyslang ``ParameterSymbol``.

    Returns:
        int | float | str: The concrete parameter value.
    """
    ptype = param_symbol.type
    value = param_symbol.value
    if ptype.isString:
        # A string ConstantValue renders with surrounding quotes ('"fast"');
        # strip them to recover the native Python string.
        text = str(value)
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        return text
    if ptype.isIntegral:
        return _sv_int_to_python(value.convertToInt())
    if ptype.isNumeric:
        return value.convertToReal()
    # Fall back to the textual form for anything exotic.
    return str(value)


_DIRECTION = {
    "In": "input",
    "Out": "output",
    "InOut": "inout",
    "Ref": "ref",
}


def _port_direction(port_symbol: Any) -> str:
    raw = str(port_symbol.direction).rsplit(".", 1)[-1]
    return _DIRECTION.get(raw, raw.lower())


def _instance_ports(instance: Any) -> List[ParamPort]:
    ports: List[ParamPort] = []
    for port in instance.body.portList:
        ptype = getattr(port, "type", None)
        width = getattr(ptype, "bitWidth", 1) if ptype is not None else 1
        ports.append(ParamPort(port.name, _port_direction(port), int(width)))
    return ports


def _instance_params(instance: Any) -> Dict[str, ParamValue]:
    """Return the overridable module parameters of an instance.

    Args:
        instance: A pyslang ``InstanceSymbol``.

    Returns:
        dict: Parameter name -> concrete value (localparams excluded).
    """
    params: Dict[str, ParamValue] = {}
    for param in instance.body.parameters:
        if getattr(param, "isLocalParam", False):
            continue
        params[param.name] = _param_value(param)
    return params


def iter_instances(compilation: Compilation) -> List[Any]:
    """Return every InstanceSymbol in the final elaborated hierarchy.

    Uses pyslang's ``visit`` which correctly descends through intermediate
    (non-target) modules to reach deeply nested instances. Instances that are
    not part of the final elaboration are skipped:

    * modules never instantiated under a top (slang creates an *uninstantiated*
      placeholder for every top-level module), and
    * instances inside a ``generate`` branch that was pruned.

    So the result reflects exactly what the design elaborates to, not every
    module that happens to be in the sources.

    Args:
        compilation: A pyslang ``Compilation``.

    Returns:
        list: Every instantiated ``InstanceSymbol`` in the design.
    """
    found: List[Any] = []

    def visitor(symbol: Any) -> None:
        if type(symbol).__name__ != "InstanceSymbol":
            return
        # Skip uninstantiated placeholders (unused top-level modules); pruned
        # generate branches are already absent from the elaborated tree.
        if getattr(symbol.body, "isUninstantiated", False):
            return
        found.append(symbol)

    compilation.getRoot().visit(visitor)
    return found


# ---------------------------------------------------------------------------
# Variant naming (sanitize + hash)
# ---------------------------------------------------------------------------

# A value may be embedded literally in a name only if it is short and made up of
# identifier-safe characters; otherwise it is replaced by a short stable hash so
# the resulting name is always a legal, filesystem-safe identifier.
_MAX_LITERAL_VALUE = 16
_SAFE_VALUE = re.compile(r"[A-Za-z0-9_]+")
_VALID_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _stable_hash(text: str, length: int) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def _value_token(value: ParamValue) -> str:
    """Human-readable, identifier-safe token for a single parameter value."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value) if value >= 0 else f"n{-value}"
    text = str(value)
    if isinstance(value, float):
        text = text.replace(".", "p").replace("-", "n")
        if _SAFE_VALUE.fullmatch(text) and len(text) <= _MAX_LITERAL_VALUE:
            return text
    elif 1 <= len(text) <= _MAX_LITERAL_VALUE and _SAFE_VALUE.fullmatch(text):
        return text
    # Long or contains illegal characters -> hash.
    return "h" + _stable_hash(text, 8)


def _canonical_signature(module: str, params: Dict[str, ParamValue]) -> str:
    parts = [f"{k}={_type_tag(v)}:{v}" for k, v in sorted(params.items())]
    return f"{module}#{';'.join(parts)}"


def _readable_name(module: str, params: Dict[str, ParamValue]) -> str:
    if not params:
        return module
    tokens = [f"{k}{_value_token(v)}" for k, v in sorted(params.items())]
    return module + "__" + "__".join(tokens)


def _hashed_name(module: str, params: Dict[str, ParamValue]) -> str:
    return f"{module}__{_stable_hash(_canonical_signature(module, params), 12)}"


def _is_clean(name: str, max_len: int) -> bool:
    return len(name) <= max_len and _VALID_IDENT.fullmatch(name) is not None


def assign_variant_names(parameterizations: List[Parameterization],
                         max_len: int = 64) -> List[Parameterization]:
    """Assign a unique, legal ``.name`` to each :class:`Parameterization`.

    Readable names (``heartbeat__N16``) are preferred. If any name in the batch
    is too long, not a legal identifier, or not globally unique, the whole batch
    falls back to a stable signature hash (``heartbeat__a1b2c3d4e5f6``),
    guaranteeing correctness even for string parameters with illegal characters
    or many parameters.

    Args:
        parameterizations (list): The parameterizations to name (mutated in
            place). All must share the same module name.
        max_len (int): Maximum length of a readable name before the batch falls
            back to hashing.

    Returns:
        list: The same ``parameterizations`` list, with ``.name`` set on each.
    """
    candidates = [_readable_name(p.module, p.params) for p in parameterizations]

    clean = all(_is_clean(name, max_len) for name in candidates)
    unique = len(set(candidates)) == len(candidates)

    if clean and unique:
        for param, name in zip(parameterizations, candidates):
            param.name = name
        return parameterizations

    # Fall back to signature hashes for the whole batch (consistent scheme).
    hashed = [_hashed_name(p.module, p.params) for p in parameterizations]
    if len(set(hashed)) != len(hashed):
        # Astronomically unlikely; widen the hash until unique.
        length = 12
        while len(set(hashed)) != len(hashed) and length < 40:
            length += 4
            hashed = [
                f"{p.module}__"
                f"{_stable_hash(_canonical_signature(p.module, p.params), length)}"
                for p in parameterizations]
    for param, name in zip(parameterizations, hashed):
        param.name = name
    return parameterizations


# ---------------------------------------------------------------------------
# Compilation building + enumeration
# ---------------------------------------------------------------------------


def build_compilation(sources: List[str], top: str,
                      defines: Optional[List[str]] = None,
                      include_dirs: Optional[List[str]] = None,
                      parameters: Optional[Dict[str, str]] = None) -> Compilation:
    """Elaborate ``sources`` with pyslang and return the ``Compilation``.

    Args:
        sources (list): Verilog/SystemVerilog source file paths.
        top (str): Name of the top module to elaborate.
        defines (list, optional): ``NAME`` or ``NAME=VALUE`` macro definitions.
        include_dirs (list, optional): Include search directories.
        parameters (dict, optional): Top-module parameter overrides (``-G``).

    Returns:
        pyslang.Compilation: The elaborated compilation.

    Raises:
        UniquifyError: If command-line parsing, option processing, or
            elaboration reports errors.
    """
    driver = pyslang.driver.Driver()
    driver.addStandardArgs()

    args = ["--single-unit", "--top", top]
    for value in (defines or []):
        args.extend(["-D", value])
    if include_dirs:
        args.extend(["--include-directory", ",".join(include_dirs)])
    for name, value in (parameters or {}).items():
        args.extend(["-G", f"{name}={value}"])
    args.extend(str(src) for src in sources)

    opts = pyslang.driver.CommandLineOptions()
    opts.ignoreProgramName = True
    if not driver.parseCommandLine(shlex.join(args), opts):
        raise UniquifyError("failed to parse slang command line")
    if not driver.processOptions():
        raise UniquifyError("failed to process slang options")
    if not driver.parseAllSources():
        raise UniquifyError("failed to parse sources")

    compilation = driver.createCompilation()

    errors = []
    for diag in compilation.getAllDiagnostics():
        severity = driver.diagEngine.getSeverity(diag.code, diag.location)
        if severity in (pyslang.DiagnosticSeverity.Error,
                        pyslang.DiagnosticSeverity.Fatal):
            errors.append(driver.diagEngine.reportAll(driver.sourceManager, [diag]))
    if errors:
        message = "elaboration reported errors:\n" + "\n".join(errors)
        if any("not a valid top-level module" in err for err in errors):
            message += (
                f"\nhint: top module {top!r} has a parameter without a "
                f"default; supply a value via the `parameters` argument "
                f"(or the fileset's param settings) so it can elaborate.")
        raise UniquifyError(message)

    return compilation


def build_compilation_from_design(design: "Design",
                                  fileset: Union[str, List[str]] = "rtl"
                                  ) -> Compilation:
    """Elaborate a design (resolving dependency filesets) and return the Compilation.

    The design is placed in a throwaway :class:`~siliconcompiler.Project` so its
    dependency filesets and aliases resolve exactly as they would in a real run.
    Sources, include dirs and defines are gathered from every resolved fileset;
    the top module and parameter overrides come from the design's first fileset.

    Args:
        design (Design): The design to elaborate.
        fileset (str | list): The design fileset(s) to build. The top module and
            parameter overrides are taken from the first. Defaults to ``"rtl"``.

    Returns:
        pyslang.Compilation: The elaborated compilation.

    Raises:
        UniquifyError: If elaboration reports errors.
    """
    from siliconcompiler import Project

    filesets = [fileset] if isinstance(fileset, str) else list(fileset)

    project = Project(design)
    for fset in filesets:
        project.add_fileset(fset)

    sources: List[str] = []
    include_dirs: List[str] = []
    defines: List[str] = []
    for lib, resolved in project.get_filesets():
        for filetype in ("systemverilog", "verilog"):
            sources.extend(lib.get_file(fileset=resolved, filetype=filetype))
        include_dirs.extend(lib.get_idir(fileset=resolved))
        defines.extend(lib.get_define(fileset=resolved))

    primary = filesets[0]
    parameters = {name: design.get_param(name, fileset=primary)
                  for name in design.getkeys("fileset", primary, "param")}
    top = design.get_topmodule(fileset=primary)

    return build_compilation(
        distinct(sources), top, defines=distinct(defines),
        include_dirs=distinct(include_dirs), parameters=parameters)


def enumerate_modules(compilation: Compilation, modules: List[str],
                      max_name_len: int = 64) -> Dict[str, List[Parameterization]]:
    """Return the distinct parameterizations of each of several ``modules``.

    Walks the full elaborated hierarchy once, groups instances of every named
    module by their concrete parameter values, records resolved port widths and
    instance paths, and assigns each group a unique variant name.

    Args:
        compilation: A pyslang ``Compilation`` (see :func:`build_compilation`).
        modules (list): Source module names to uniquify.
        max_name_len (int): Maximum length of a readable variant name before
            falling back to a hash.

    Returns:
        dict: ``{module: [Parameterization, ...]}`` for every requested module,
        each list ordered deterministically by signature (empty if the module is
        never instantiated). Variant names are unique across all modules because
        each is prefixed with its module name.
    """
    # Preserve request order and tolerate duplicates.
    buckets: Dict[str, Dict[Any, Parameterization]] = {
        module: {} for module in dict.fromkeys(modules)}

    for instance in iter_instances(compilation):
        name = instance.definition.name
        if name not in buckets:
            continue
        params = _instance_params(instance)
        param = Parameterization(name, params, _instance_ports(instance))
        entry = buckets[name].setdefault(param.signature, param)
        entry.instances.append(instance.hierarchicalPath)

    result: Dict[str, List[Parameterization]] = {}
    for module, by_signature in buckets.items():
        combos = sorted(by_signature.values(), key=lambda p: str(p.signature))
        for param in combos:
            param.instances = sorted(set(param.instances))
        assign_variant_names(combos, max_len=max_name_len)
        result[module] = combos
    return result


def enumerate_module(compilation: Compilation, module: str,
                     max_name_len: int = 64) -> List[Parameterization]:
    """Return the distinct :class:`Parameterization`\\ s of a single ``module``.

    Thin wrapper over :func:`enumerate_modules`.

    Args:
        compilation: A pyslang ``Compilation``.
        module (str): Source module name to uniquify.
        max_name_len (int): Maximum length of a readable variant name before
            falling back to a hash.

    Returns:
        list: :class:`Parameterization` objects (empty if ``module`` is never
        instantiated).
    """
    return enumerate_modules(compilation, [module], max_name_len=max_name_len)[module]


def enumerate_design(design: "Design", modules: Union[str, List[str]],
                     fileset: str = "rtl", max_name_len: int = 64
                     ) -> Union[List[Parameterization],
                                Dict[str, List[Parameterization]]]:
    """Enumerate module(s) from a SiliconCompiler Design.

    Elaborates the design via :func:`build_compilation_from_design` (which
    resolves dependency filesets), then enumerates the requested module(s).

    Args:
        design (Design): The design to elaborate. Submodules may live in
            dependency filesets.
        modules (str | list): A single module name (returns a list) or a list of
            names (returns a ``{module: [...]}`` dict).
        fileset (str): The design fileset to build. Defaults to ``"rtl"``.
        max_name_len (int): Maximum length of a readable variant name before
            falling back to a hash.

    Returns:
        list | dict: A list of :class:`Parameterization` when ``modules`` is a
        single name, otherwise a ``{module: [Parameterization, ...]}`` dict.
    """
    compilation = build_compilation_from_design(design, fileset)
    if isinstance(modules, str):
        return enumerate_module(compilation, modules, max_name_len=max_name_len)
    return enumerate_modules(compilation, modules, max_name_len=max_name_len)
