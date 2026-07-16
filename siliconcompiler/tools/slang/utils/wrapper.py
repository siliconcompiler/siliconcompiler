# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
"""Generate a parameterized wrapper plus param-less variants for a module.

A hardened macro has no parameters. To keep a parameterized module usable after
hardening we emit, for a module ``M`` and the set of concrete parameterizations
discovered by :mod:`~siliconcompiler.tools.slang.utils.uniquify`:

* one **variant** module per parameterization -- a copy of ``M`` renamed to the
  variant name with its parameters baked to the concrete values (each parameter's
  declared default is rewritten in place), so it elaborates to a fixed,
  parameter-free design. The body is preserved verbatim, so the variant adds no
  extra hierarchy: the hardened macro is ``M``'s logic directly, not ``M``
  wrapped in another instance. Each variant is hardened into its own macro.

* one **wrapper** module that keeps ``M``'s original name, parameters and
  (parameterized) port list, and whose body is an elaboration-time ``generate``
  dispatch selecting the matching variant. Any parameter combination that was
  not hardened triggers an elaboration ``$error``.

In the parent design the wrapper replaces ``M``'s RTL (via an alias) and the
variants are supplied as hardened macros. A variant carries ``M``'s full body, so
in its own hardening run it needs only ``M``'s submodule dependencies (the
original ``M`` may be present too but is unused, and the renamed variant never
collides with it).

This module only produces SystemVerilog text; running the elaboration and
building the :class:`~uniquify.Parameterization` list is the job of
:mod:`uniquify`.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, TypedDict

from siliconcompiler.tools.slang import pyslang
from siliconcompiler.tools.slang.utils import uniquify
from siliconcompiler.tools.slang.utils.uniquify import (
    Compilation, ParamValue, Parameterization, UniquifyError)


class GeneratedModule(TypedDict):
    """Generated SystemVerilog for one uniquified module.

    Attributes:
        wrapper (str): Source for the parameterized wrapper module.
        variants (dict): ``{variant_name: source}`` for each param-less variant.
    """
    wrapper: str
    variants: Dict[str, str]


DEFAULT_INSTANCE_NAME = "u_impl"

# Leading trivia (file banner comments / whitespace) that precedes the module
# keyword in the printed header; stripped so the wrapper starts at ``module``.
_LEADING_TRIVIA = re.compile(r"\A(?:\s*(?://[^\n]*|/\*.*?\*/))*\s*", re.DOTALL)

# Variable data type on a port declaration (e.g. ``output reg [N-1:0] out``).
# The direction keyword only appears in port declarations -- never in the
# parameter list -- so keying on it is safe.
_PORT_VAR_TYPE = re.compile(
    r"\b(input|output|inout)\s+(?:reg|logic|bit|var|wire)\b")


def _force_net_ports(header: str) -> str:
    """Drop variable data types from port declarations so ports are nets.

    A wrapper port is driven by the selected variant instance, and in plain
    Verilog an instance output can only drive a net -- not a ``reg``/variable.
    The original module may declare e.g. ``output reg [N-1:0] out``; strip the
    ``reg``/``logic``/``var`` so the wrapper declares ``output [N-1:0] out``.
    """
    return _PORT_VAR_TYPE.sub(r"\1", header)


def format_param_value(value: ParamValue) -> str:
    """Render a Python parameter value as a SystemVerilog literal.

    Args:
        value: The parameter value (``int``, ``float``, ``bool`` or ``str``).

    Returns:
        str: A SystemVerilog literal (strings are quoted and escaped).
    """
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    # String: quote and escape embedded quotes/backslashes.
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _module_definition_syntax(compilation: Compilation, module: str):
    """Return the ``ModuleDeclarationSyntax`` for ``module``.

    Args:
        compilation: A pyslang ``Compilation``.
        module (str): The module to look up.

    Returns:
        The module's declaration syntax node.

    Raises:
        UniquifyError: If ``module`` is not defined in the compilation.
    """
    for instance in uniquify.iter_instances(compilation):
        if instance.definition.name == module:
            return instance.definition.syntax
    raise UniquifyError(f"module {module!r} not found in compilation")


def get_module_header(compilation: Compilation, module: str) -> str:
    """Return the wrapper ``module ... (...);`` header text for ``module``.

    Preserves the module's original parameters and parameterized port widths, but
    forces port declarations to be nets (dropping ``reg``/``logic``/``var``) --
    the wrapper's ports are driven by the selected variant instance, which
    requires nets. Any file-banner comment preceding ``module`` is stripped.

    Args:
        compilation: A pyslang ``Compilation``.
        module (str): The module whose header to extract.

    Returns:
        str: The header text, starting at ``module`` and ending at ``);``, with
        net-typed ports.

    Raises:
        UniquifyError: If ``module`` is not defined in the compilation.
    """
    header = _module_definition_syntax(compilation, module).header
    printer = pyslang.syntax.SyntaxPrinter(compilation.sourceManager)
    printer.setIncludeDirectives(False)
    printer.setIncludeComments(True)
    printer.setIncludeTrivia(True)
    text = printer.print(header).str()
    return _force_net_ports(_LEADING_TRIVIA.sub("", text).strip())


def generate_variant_module(compilation: Compilation,
                            param: Parameterization,
                            source_module: str) -> str:
    """Generate the param-less variant module for one parameterization.

    The variant is the original ``source_module`` copied verbatim, renamed to
    ``param.name``, with its parameters baked to the concrete values: each baked
    parameter's declared default is rewritten to the resolved value (or a default
    is inserted where the source declared none). No extra hierarchy is added --
    the hardened macro is the module's own logic, not the module wrapped in
    another instance. Both ANSI (``#(...)``) and non-ANSI (body ``parameter``)
    declaration styles are handled.

    Args:
        compilation: A pyslang ``Compilation`` containing ``source_module``.
        param (Parameterization): The parameterization to specialise.
        source_module (str): Name of the original parameterized module.

    Returns:
        str: SystemVerilog source for the variant module.

    Raises:
        UniquifyError: If ``source_module`` is not defined in the compilation.
    """
    syntax = _module_definition_syntax(compilation, source_module)
    rng = syntax.sourceRange
    source = compilation.sourceManager.getSourceText(rng.start.buffer)
    base = rng.start.offset
    text = source[base:rng.end.offset]

    # Collect (start, end, replacement) edits in buffer offsets relative to the
    # sliced module text, then apply them right-to-left so earlier offsets stay
    # valid.
    edits = []

    # Rename the module (declaration name token only, never body references).
    name_tok = syntax.header.name
    edits.append((name_tok.range.start.offset - base,
                  name_tok.range.end.offset - base, param.name))

    # Bake each overridable parameter to its concrete value. Visiting the whole
    # module catches both the ANSI parameter-port list and non-ANSI body
    # `parameter` declarations.
    param_decls = []
    syntax.visit(
        lambda node: param_decls.append(node)
        if type(node).__name__ == "ParameterDeclarationSyntax" else None)
    for decl in param_decls:
        if decl.keyword.valueText != "parameter":       # skip localparams
            continue
        for declarator in decl.declarators:
            pname = declarator.name.valueText
            if pname not in param.params:
                continue
            value = format_param_value(param.params[pname])
            init = declarator.initializer
            if init is not None:
                expr = init.expr.sourceRange
                edits.append((expr.start.offset - base,
                              expr.end.offset - base, value))
            else:                                        # no default -> insert
                pos = declarator.name.range.end.offset - base
                edits.append((pos, pos, f" = {value}"))

    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]

    if not text.endswith("\n"):
        text += "\n"
    return text


def _match_condition(params: Dict[str, ParamValue]) -> str:
    terms = [f"({name} == {format_param_value(value)})"
             for name, value in sorted(params.items())]
    return " && ".join(terms)


def generate_wrapper_module(header: str, combos: List[Parameterization],
                            instance_name: str = DEFAULT_INSTANCE_NAME,
                            error_message: Optional[str] = None) -> str:
    """Generate the parameterized wrapper body around ``header``.

    Each parameterization contributes one ``generate`` branch instantiating its
    variant; a final ``else`` branch emits an elaboration ``$error`` for
    parameter combinations that were not hardened.

    Args:
        header (str): The module header (see :func:`get_module_header`).
        combos (list): The parameterizations of the module.
        instance_name (str): Instance name for the selected variant.
        error_message (str, optional): Custom message for the ``$error`` on an
            unhardened combination.

    Returns:
        str: SystemVerilog source for the wrapper module.
    """
    module = combos[0].module if combos else "?"
    if error_message is None:
        error_message = (f"no hardened variant of {module} exists for the "
                         f"requested parameters")

    branches = []
    for combo in combos:
        ports = ", ".join(f".{p.name}({p.name})" for p in combo.ports)
        keyword = "if" if not branches else "else if"
        branches.append(
            f"        {keyword} ({_match_condition(combo.params)}) "
            f"begin : g_{combo.name}\n"
            f"            {combo.name} {instance_name} ({ports});\n"
            f"        end")

    branches.append(
        f"        else begin : g_invalid\n"
        f'            $error("{error_message}");\n'
        f"        end")

    body = "\n".join(branches)
    return (
        f"{header}\n"
        f"    generate\n"
        f"{body}\n"
        f"    endgenerate\n"
        f"endmodule\n"
    )


def generate_uniquified(compilation: Compilation, module: str,
                        combos: Optional[List[Parameterization]] = None,
                        instance_name: str = DEFAULT_INSTANCE_NAME
                        ) -> GeneratedModule:
    """Generate the wrapper + all variant modules for ``module``.

    Args:
        compilation: A pyslang ``Compilation`` (see
            :func:`uniquify.build_compilation`).
        module (str): The parameterized module to uniquify.
        combos (list, optional): Precomputed :class:`~uniquify.Parameterization`
            list; if omitted it is derived via
            :func:`uniquify.enumerate_module`.
        instance_name (str): Name for the instantiated sub-module in generated
            modules.

    Returns:
        dict: ``{"wrapper": <str>, "variants": {variant_name: <str>, ...}}``.

    Raises:
        UniquifyError: If ``module`` is not instantiated, or has no overridable
            parameters (nothing to uniquify).
    """
    if combos is None:
        combos = uniquify.enumerate_module(compilation, module)
    if not combos:
        raise UniquifyError(f"module {module!r} is not instantiated")
    if not any(c.params for c in combos):
        raise UniquifyError(
            f"module {module!r} has no parameters; nothing to uniquify")

    header = get_module_header(compilation, module)

    variants = {
        combo.name: generate_variant_module(compilation, combo, module)
        for combo in combos
    }
    wrapper = generate_wrapper_module(header, combos, instance_name)

    return {"wrapper": wrapper, "variants": variants}


def generate_modules(compilation: Compilation, modules: List[str],
                     instance_name: str = DEFAULT_INSTANCE_NAME
                     ) -> Dict[str, GeneratedModule]:
    """Generate the wrapper + variants for several modules in one pass.

    Args:
        compilation: A pyslang ``Compilation``.
        modules (list): Parameterized module names to uniquify.
        instance_name (str): Name for the instantiated sub-module.

    Returns:
        dict: ``{module: {"wrapper": ..., "variants": {...}}}`` for each module.

    Raises:
        UniquifyError: If any named module is not instantiated or has no
            overridable parameters.
    """
    enumerated = uniquify.enumerate_modules(compilation, modules)
    return {
        module: generate_uniquified(
            compilation, module, combos=combos, instance_name=instance_name)
        for module, combos in enumerated.items()
    }
