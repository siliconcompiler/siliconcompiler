.. _uniquify_modules:

Hardening parameterized modules (uniquify)
==========================================

.. note::
    **Beta feature.** Uniquify (:class:`.Uniquified`) is new; its API and
    generated output may change in a future release.

The :ref:`hardened-module tutorial <hardened_modules>` hardened a single,
*unparameterized* module and instantiated it in a parent -- packaging the macro,
blackboxing the RTL and injecting the library all by hand. This tutorial tackles
the case that flow cannot: a **parameterized** module instantiated with several
different parameter values.

.. admonition:: How this differs from the hardened-module tutorial
   :class: tip

   The :ref:`hardened-module tutorial <hardened_modules>` teaches the underlying
   *mechanism* -- harden a module, blackbox it, inject the macro -- by hand for
   one fixed module. If you have not read it, start there.

   This tutorial is about the problem that mechanism alone cannot solve. A
   hardened macro is a fixed netlist with **no parameters**, so a post-synthesis
   block named ``heartbeat`` no longer has an ``N`` for a parent's
   ``heartbeat #(.N(8))`` to bind to -- and the parent uses ``N`` = 8, 24 *and*
   48. :class:`.Uniquified` resolves this automatically: it discovers which
   parameter values are actually used, generates a hardenable variant for each
   plus a wrapper that restores the original interface, and drives the whole
   harden-and-inject flow for every variant at once.

Given a design and the names of the parameterized modules to harden,
:class:`.Uniquified`:

1. **enumerates** every concrete parameter combination the modules are actually
   instantiated with (by elaborating the design with `slang <https://github.com/MikePopoloski/slang>`_),
2. **generates**, for each combination, a parameter-free *variant* to harden
   (e.g. ``heartbeat__N8``) plus a parameterized *wrapper* that keeps the
   original module's name and interface and dispatches to the matching variant,
3. **registers** filesets for those sources on the design, then lets you
   **build** each variant into a macro and **wire up** the wrappers and macros
   into a parent :class:`.ASIC` project.

This mirrors how ``lambdalib`` maps an abstract cell onto hardened
implementations, but generated automatically from how the modules are used.

.. note::
    Unparameterized modules are handled too. A module with no overridable
    parameters is already hardenable, so no wrapper is generated for it -- it is
    hardened directly and blackboxed at wireup, i.e. :class:`.Uniquified` does
    exactly what the :ref:`hardened-module tutorial <hardened_modules>` does by
    hand. A single :class:`.Uniquified` can therefore harden a mix of
    parameterized and unparameterized modules in one shot.

All of the code below is contained in the
`example script <https://github.com/siliconcompiler/siliconcompiler/blob/main/examples/uniquify/uniquify.py>`_.
To inspect what uniquify generates (no EDA tools required):

.. code-block:: bash

    smake main

and to run the full flow (requires yosys and OpenROAD):

.. code-block:: bash

    smake harden


The design
----------

The parent instantiates a parameterized ``heartbeat`` counter with several
distinct widths (``N``), plus a ``prescaler``. Note that ``N=24`` is used twice
-- uniquify hardens it only once.

.. literalinclude:: examples/uniquify/heartbeat_top.v
    :caption: heartbeat_top.v
    :language: verilog

.. literalinclude:: examples/uniquify/heartbeat.v
    :caption: heartbeat.v
    :language: verilog


Step 1: Define the modules and the parent
-----------------------------------------

Each parameterized module to be hardened must be its own reusable
:class:`.Design` (uniquify aliases the module's RTL to a generated wrapper, so it
needs a design to alias). The parent depends on their RTL so it elaborates.

.. literalinclude:: examples/uniquify/uniquify.py
    :language: python
    :caption: The parameterized modules
    :lines: 34-51

.. literalinclude:: examples/uniquify/uniquify.py
    :language: python
    :caption: The parent design
    :lines: 54-64


Step 2: Construct the ``Uniquified`` helper
-------------------------------------------

Pass the parent design (or a :class:`.Project`) and the module names to
uniquify. Construction enumerates the parameter combinations and generates the
wrappers/variants **in memory** -- it writes nothing to disk and runs no tools --
and registers the new filesets on the design.

.. literalinclude:: examples/uniquify/uniquify.py
    :language: python
    :caption: Setting up uniquification
    :lines: 26-28,67-73

The filesets registered on the design are:

* ``rtl.<module>.wrapper`` -- the parameterized wrapper (keeps the module's name
  and interface), one per module.
* ``rtl.hardened.<variant>`` -- one parameter-free variant per combination, the
  top that gets hardened into a macro.
* ``rtl.wrapper`` -- an aggregate that pulls every per-module wrapper at once.


Step 3: Inspect what was generated
----------------------------------

The helper exposes its results as plain state. The ``main`` function prints the
variants and fileset names, then writes the sources so you can read a wrapper:

.. literalinclude:: examples/uniquify/uniquify.py
    :language: python
    :caption: Inspecting the results
    :lines: 105-120

For this design that reports three ``heartbeat`` variants (``N`` = 8, 24, 48 --
the duplicate ``N=24`` merged) and two ``prescaler`` variants:

.. code-block:: text

    'heartbeat' -> 3 variant(s): ['heartbeat__N24', 'heartbeat__N48', 'heartbeat__N8']
    'prescaler' -> 2 variant(s): ['prescaler__W4', 'prescaler__W8']

The generated wrapper keeps the ``heartbeat`` name and its ``N`` parameter, and
uses a ``generate`` block to select the matching hardened variant. If a design
ever requests a parameter combination that was not hardened, elaboration fails
loudly via ``$error`` rather than silently building the wrong thing:

.. code-block:: verilog
    :caption: heartbeat.wrapper.v (generated)

    module heartbeat #(
        parameter N = 8
    ) (
        input      clk,
        input      nreset,
        output out
    );
        generate
            if ((N == 24)) begin : g_heartbeat__N24
                heartbeat__N24 u_impl (.clk(clk), .nreset(nreset), .out(out));
            end
            else if ((N == 48)) begin : g_heartbeat__N48
                heartbeat__N48 u_impl (.clk(clk), .nreset(nreset), .out(out));
            end
            else if ((N == 8)) begin : g_heartbeat__N8
                heartbeat__N8 u_impl (.clk(clk), .nreset(nreset), .out(out));
            end
            else begin : g_invalid
                $error("no hardened variant of heartbeat exists for the requested parameters");
            end
        endgenerate
    endmodule


Step 4: Harden the variants
---------------------------

:meth:`.Uniquified.build` hardens the selected variants (all of them by default)
into :class:`.StdCellLibrary` macros. Pass a ``target`` -- a SiliconCompiler
target callback ``fn(project)`` that configures the PDK, flow and constraints on
each variant's ASIC run -- exactly as you would for a normal build:

.. literalinclude:: examples/uniquify/uniquify.py
    :language: python
    :caption: The target used for each variant (and the parent)
    :lines: 76-85

.. literalinclude:: examples/uniquify/uniquify.py
    :language: python
    :caption: Hardening every variant
    :lines: 93-94

Each variant is built under its own job (``jobname=<variant>``) beneath the
helper's ``libdir``, and the resulting macro is persisted so a later run reuses
it. ``build`` returns a ``{variant: StdCellLibrary}`` mapping. Pass
``parallel=True`` to harden the variants concurrently, or ``macros="heartbeat"``
/ ``macros="heartbeat__N*"`` to rebuild a subset.


Step 5: Wire up the parent
--------------------------

Finally, build the parent. This is where the mechanism from the
:ref:`hardened-module tutorial <hardened_modules>` -- alias the module's RTL,
inject the macro with ``add_asiclib`` -- is applied, but you do not write it out
by hand: :meth:`.Uniquified.wireup` does it for every variant at once. It aliases
each module's RTL to its generated *wrapper* (so synthesis elaborates the
dispatch instead of the original parameterized RTL, the one twist beyond the
hardened-module flow) and injects all the hardened macros:

.. literalinclude:: examples/uniquify/uniquify.py
    :language: python
    :caption: Building the parent with the wrappers and macros
    :lines: 88-102

.. note::
    ``wireup`` requires every used variant to have a built (or loaded) macro, and
    raises otherwise. The generated wrapper has a branch for each *enumerated*
    variant, so an unbuilt-but-used variant still matches its own branch (it does
    not reach the ``$error`` default) -- what fails is the missing hardened
    implementation. The ``$error`` branch only guards parameter combinations that
    were never enumerated at all. Call :meth:`.Uniquified.build` first, or
    :meth:`.Uniquified.load_macros` to reuse macros from a previous run.


Conclusion
----------

Starting from a parent that instantiates a parameterized module with several
different parameter values, uniquify:

- discovered the concrete parameterizations in use,
- generated a hardenable variant for each and a parameterized wrapper to
  dispatch to them,
- hardened the variants into reusable macros, and
- wired the wrappers and macros into the parent build.

See the :ref:`Uniquify API <uniquify_api>` for the full class reference.
