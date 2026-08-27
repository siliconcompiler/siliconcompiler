.. _soda_tutorial:

From a model to silicon (SODA)
==============================

`SODA Synthesizer <https://github.com/pnnl/soda-opt>`_ compiles a
machine learning model into accelerator :term:`RTL`. Its front end, ``soda-opt``,
works in :term:`MLIR`: a model exported to the TOSA dialect is lowered to
linalg, the compute worth accelerating is outlined into a kernel, that kernel is
optimized for :term:`high-level synthesis`, and an HLS tool turns it into
Verilog.

SiliconCompiler drives that front end and then keeps going. Everything from the
generated Verilog onward -- :term:`synthesis`, :term:`place-and-route`,
:term:`signoff` -- is the ordinary :ref:`ASIC flow <builtin_flows>`, so a model
reaches :term:`GDSII` in a single job, with one manifest recording what every
stage did.

.. admonition:: Who this is for / prerequisites
   :class: note

   You should be comfortable with the :ref:`quickstart build <quickstart_guide>`
   and with the idea of a design whose sources are not Verilog (see
   :ref:`Hardware design frontends <hw_frontends>`).
   You do **not** need to know MLIR to follow along; the one thing worth
   knowing is that a ``.mlir`` file is a program in a *dialect*, and that the
   flow's job is to rewrite it into progressively lower-level dialects until it
   is something an HLS tool can read.

   The full flow needs ``mlir``, ``soda``, ``bambu``, ``yosys``, ``openroad``,
   ``opensta`` and ``klayout``, plus FreePDK45 from ``lambdapdk``.

Installing the toolchain
------------------------

Two installs, and the order matters:

.. code-block:: bash

   sc-install mlir soda

``mlir`` builds llvm-project -- ``mlir-opt``, ``mlir-translate``, ``llvm-link``,
``opt`` and ``clang`` -- at the revision ``soda-opt`` is developed against.

``soda`` then builds ``soda-opt`` and ``soda-translate`` against that install.
The order matters and is not a convenience: ``soda-opt`` is an out-of-tree MLIR
project that links against MLIR's C++ libraries, so it can only be built against
that exact LLVM revision. A distribution ``mlir-tools`` package will not do, and
the ``soda`` script stops with an explanation rather than guessing. Naming both
on one command line is enough: they are installed left to right, and a failure in
``mlir`` stops before ``soda`` is attempted.

The whole group, including the backend, is one command:

.. code-block:: bash

   sc-install -group asic-soda

.. important::

   **The HLS step needs a Bambu built against clang 15 or newer.** LLVM 19 emits
   opaque pointers (``ptr``) unconditionally -- typed pointers were removed in
   LLVM 17 -- and an older Bambu front end rejects the IR outright:

   .. code-block:: text

      error: expected type
      define void @forward_kernel(ptr %0, ptr %1, ptr %2) {
                                  ^

   SiliconCompiler's ``install-bambu.sh`` gives Bambu clang-16 on **ubuntu24**,
   but clang-11 on ubuntu22 and clang-8 on ubuntu20. So ubuntu24 is where the
   flow runs end to end; elsewhere the MLIR front end works and high-level
   synthesis does not. ``sc-install mlir`` checks the Bambu on your ``PATH`` and
   warns before it starts building, rather than letting this surface an hour
   later at the last node.

   Pointing Bambu at the clang this toolchain installs is not an option, which is
   the obvious thing to try: Bambu compiles a set of *plugins* against each
   supported clang's internals, so the versions it accepts are built in rather
   than configured, and there is no ``--with-clang=<path>``. Its ``configure``
   knows clang 4-13 and 16 -- on the pinned release and on upstream ``main``
   alike -- so clang 19 cannot be used until Bambu itself ports its plugins to
   it.

The example
-----------

``examples/soda`` holds ``mm``, ``mm-no_weights`` model: a stateless
batched matrix multiply, which is what ``torch.matmul`` over a ``[1, 4, 8]`` and
a ``[1, 8, 4]`` tensor exports to.

.. literalinclude:: examples/soda/mm.mlir
   :language: text
   :caption: examples/soda/mm.mlir

It is checked in so that the flow can be built without a PyTorch install.
``smake model`` regenerates it by re-running the export, which is the one target
that needs ``pip install -r requirements.txt`` in the example directory first;
nothing else here does.

Two things about this file decide everything downstream.

**The entry function is called** ``forward``. ``soda-opt`` outlines the kernel it
finds into ``<function>_kernel``, so the synthesizable kernel here is
``forward_kernel``.

**The topmodule is therefore** ``forward_kernel``, **not** ``mm``. Bambu is
pointed at the design's topmodule, and everything after it -- synthesis, the
:term:`SDC`, the final GDS -- names that kernel. Getting this wrong points the
HLS tool at a function that does not exist; the ``soda`` task notices and says
so, but it is easier to get right the first time.

Building it
-----------

The design's sources are MLIR rather than Verilog. Everything else about it is an
ordinary :ref:`design <own_design_tutorial>`:

.. literalinclude:: examples/soda/make.py
   :language: python
   :pyobject: SODADesign
   :caption: examples/soda/make.py

``mm.sdc`` constrains the clock port Bambu gives the RTL it generates, which is
called ``clock``:

.. literalinclude:: examples/soda/mm.sdc
   :language: tcl
   :caption: examples/soda/mm.sdc

That one file is read three times over a build: by Bambu as the period its
scheduler has to hit, then by synthesis, then by place-and-route. Changing it
changes the hardware, not just the report.

Selecting the flow is the whole of the rest -- a model reaches :term:`GDSII` in
one job, and the only thing that says "SODA" is which flow was chosen:

.. literalinclude:: examples/soda/make.py
   :language: python
   :pyobject: asic

Run it, and every other stage, as an :ref:`smake <howto_smake>` target:

.. code-block:: bash

   cd examples/soda
   smake elaborate     # MLIR to Verilog: soda-opt plus Bambu, nothing else
   smake syn           # ...and on through synthesis and timing
   smake asic          # ...and on to GDSII

What the flow does
------------------

``SODAASICFlow`` is the ordinary ASIC flow with the SODA front end in front of
it. The front end on its own is one of the flows in
:mod:`~siliconcompiler.flows.sodaflow`, and it is worth knowing what each of its
nodes is for, because that is where a build goes wrong:

.. list-table::
   :header-rows: 1
   :widths: 18 20 62

   * - Node
     - Tool
     - What it does
   * - ``tosa2linalg``
     - ``mlir-opt``
     - Lowers the TOSA operations to their linalg equivalents, still on tensors.
   * - ``bufferize``
     - ``mlir-opt``
     - Puts that linalg on buffers and turns the function's result into an
       out-parameter. Hardware has no notion of returning a tensor.
   * - ``soda``
     - ``soda-opt``
     - Outlines the kernel, optimizes it for HLS, lowers it to the LLVM dialect.
       This is the node the three strategies differ in.
   * - ``translate``
     - ``mlir-translate``
     - Emits LLVM IR, then strips the ``llvm.stacksave`` / ``llvm.stackrestore``
       intrinsics MLIR brackets stack buffers with, which an HLS backend cannot
       read.
   * - ``runtime``
     - ``clang``
     - Compiles a C support module to LLVM IR -- by default the bundled
       ``memref_copy.c``. It has no design input, so it is a second entry node
       and runs alongside the rest.
   * - ``link``
     - ``llvm-link``
     - Merges that module in, but only if the kernel calls it. Bufferized code
       lowers ``memref.copy`` to a ``memrefCopy`` call that upstream expects from
       MLIR's runner library; there is no runtime to link against in hardware, so
       the definition goes into the module.
   * - ``convert``
     - ``bambu``
     - High-level synthesis: LLVM IR to Verilog.

Everything downstream of ``convert`` is the flow any Verilog design uses.

The three strategies
--------------------

The ``soda`` node is where SODA earns its name, and it offers three ways to
lower the outlined kernel:

``baseline``
   No HLS-oriented optimization: linalg straight to the LLVM dialect. This is
   the reference -- what the HLS tool makes of code nobody prepared for it.

``optimized``
   Runs ``soda-opt``'s Bambu pipeline first: the loop nest is tiled, given local
   buffers, unrolled and scalar-replaced. This is the default, and the
   difference between it and the baseline is the result the SODA papers report.

``transformed``
   Applies a schedule written in MLIR's transform dialect instead of the fixed
   pipeline, then lowers. This is how a design expresses a strategy the
   pipeline's knobs cannot. It needs a schedule to be worth running, so unlike
   the other two it is not exercised by the example -- write the schedule first,
   then hand it to the task.

Each strategy is a flow of its own, so picking one is picking a flow:

.. code-block:: python

   from siliconcompiler.flows.sodaflow import SODABaselineElaborationFlow

   # The front end on its own: MLIR in, Verilog out.
   project.set_flow(SODABaselineElaborationFlow())

Any flow that elaborates a design takes one as its ``frontend``, which is the
whole of how the SODA path reaches synthesis and GDSII -- there is no SODA
backend, and no language string to spell:

.. code-block:: python

   project.set_flow(SynthesisFlow(frontend=SODABaselineElaborationFlow()))
   project.set_flow(ASICFlow(frontend=SODABaselineElaborationFlow()))

``SODAASICFlow`` is that last line with the strategy named instead, which is
what the example uses:

.. code-block:: python

   project.set_flow(SODAASICFlow(strategy="baseline"))

``make.py`` in the example runs the comparison the strategies exist for:

.. code-block:: bash

   smake compare

which synthesizes the baseline and the optimized kernel and prints Bambu's own
estimate beside what synthesis actually produced -- how well the HLS tool
predicted the hardware, and how much the optimization bought.

Turning the knobs
-----------------

Every stage of the optimization pipeline is a task setter, so a design can be
swept over them without touching the flow. Reach the task with ``find_task``
once the flow is in the project:

.. code-block:: python

   from siliconcompiler.tools.soda.opt import OptimizedTask

   project.set_flow(SODAASICFlow())

   soda = OptimizedTask.find_task(project)
   soda.set_soda_fullunrolls(3)      # unroll one more level of the loop nest
   soda.set_soda_tilesize(2)         # tile every affine loop
   soda.add_soda_permutation([1, 2, 0])
   soda.set_soda_buffertrick(False)  # no local buffers for the loop nest

.. important::

   A flow *copies* the task it is handed, so configuring a task object before
   passing it to ``Flowgraph.node()`` has no effect. ``find_task`` after
   ``set_flow`` is the way to reach the one the flow will actually run.

``set_soda_fullunrolls`` is the one that moves the result most: each application
unrolls one more level, trading cells for cycles. ``smake unrolled 3`` in the
example synthesizes with a different depth so the trade is visible.

The transform-dialect strategy takes its schedule the same way. The schedule is
your own MLIR file, holding a ``transform.named_sequence @__transform_main`` that
rewrites the outlined kernel; it is required, so the flow stops at validation
without one rather than lowering the kernel unrewritten:

.. code-block:: python

   from siliconcompiler.tools.soda.opt import TransformedTask

   project.set_flow(SODAASICFlow(strategy="transformed"))
   TransformedTask.find_task(project).set_soda_schedule("my_schedule.mlir")

The support module the kernel is linked against is a knob too -- any C file whose
LLVM IR should end up inside the kernel goes here, and the module it produces is
named after it:

.. code-block:: python

   from siliconcompiler.tools.mlir.compile import RuntimeTask
   from siliconcompiler.tools.mlir.link import LinkTask

   RuntimeTask.find_task(project).set_mlir_source("helpers.c")
   # ...which the link step picks up as "the upstream module that is not the
   # kernel", so it needs no name of its own. What it does need is the symbol
   # that decides whether merging is worth it:
   LinkTask.find_task(project).set_mlir_requiredsymbol("myHelper")

and the HLS step has its own:

.. code-block:: python

   from siliconcompiler.tools.bambu.convert import ConvertTask as BambuConvertTask

   bambu = BambuConvertTask.find_task(project)
   bambu.set_bambu_memorychannels(2)
   bambu.set_bambu_experimentalsetup("BAMBU-BALANCED-MP")
   # Anything without a setter of its own still reaches the command line:
   bambu.add_commandline_option("--max-sim-cycles=2000000")

The target supplies the rest. FreePDK45's Nangate45 library already carries
``--device=nangate45`` for Bambu.

Where to look when it fails
---------------------------

The front end fails in a small number of recognizable ways:

*The* ``soda`` *node emits nothing to outline.* The module reached it without a
kernel to find -- usually because ``bufferize`` did not produce linalg on
buffers. Read ``bufferize/0/outputs/<top>.mlir``; if it still mentions ``tosa.``
or ``tensor<``, the lowering is what to fix.

*The kernel has the wrong name.* The ``soda`` node warns when the kernel it
outlined is not the design's topmodule. Rename the topmodule to match, or point
``set_soda_anchorfunc`` at the function you meant.

*Bambu rejects the LLVM IR.* Look at ``link/0/outputs/<top>.ll``. An unresolved
``memrefCopy`` means the ``runtime`` node did not run or the ``link`` node
decided it was not needed; ``translate``'s intrinsic strip covers the other
common case.

*A pass name is not recognized.* ``soda-opt`` and ``mlir-opt`` have to come from
the same llvm-project revision. ``sc-install mlir`` then ``sc-install soda``, in
that order, is what keeps them in step.

*Bambu reports* ``error: expected type`` *on a* ``ptr`` *argument.* Its front-end
compiler is older than clang 15 and cannot read opaque pointers. See the install
note above; this is a property of the Bambu build, not of the design.

For the pass-by-pass view, turn on the IR dump -- verbose, but it is the only
practical way to see which pass broke a lowering:

.. code-block:: python

   OptimizedTask.find_task(project).set_soda_printirafterall(True)
