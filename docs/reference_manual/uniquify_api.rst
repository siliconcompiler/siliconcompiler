.. _uniquify_api:

Uniquify API
------------

This chapter describes the public API for hardening parameterized modules. For a
worked walkthrough see the :ref:`uniquify tutorial <uniquify_modules>`.

A hardened macro is parameter-free, so a parameterized module cannot be hardened
and reused directly. :class:`.Uniquified` discovers the concrete parameter
combinations a design uses, generates a parameter-free variant for each (to
harden) plus a parameterized wrapper that dispatches to them, and integrates the
results into a SiliconCompiler flow.

.. currentmodule:: siliconcompiler.tools.slang.utils.macro

Uniquified
==========

.. autosummary::
    :nosignatures:

    Uniquified.write
    Uniquified.build
    Uniquified.load_macros
    Uniquified.wireup
    Uniquified.manifest
    Uniquified.instance_path

.. autoclass:: siliconcompiler.tools.slang.utils.macro.Uniquified
    :members:
    :special-members: __init__

Packaging a macro
=================

.. autofunction:: siliconcompiler.tools.slang.utils.macro.build_macro
