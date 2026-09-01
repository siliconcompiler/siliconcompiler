.. _soda_frontend:

MLIR frontend (SODA)
--------------------

SiliconCompiler can take a machine learning model straight to hardware using
`SODA Synthesizer <https://github.com/pnnl/soda-opt>`_, whose front end
works in :term:`MLIR`.
A model converted to the TOSA dialect -- the form PyTorch, TensorFlow and
TFLite models are brought into -- is then lowered to linalg, a kernel is
outlined and optimized for high-level synthesis by ``soda-opt``, and
:ref:`Bambu <c_hls_frontend>` turns that kernel into Verilog for the rest of the
flow.

The design's source fileset holds a ``.mlir`` file instead of Verilog, and the
topmodule is the *outlined kernel*: ``soda-opt`` names it after the function it
came from, so a model whose entry point is ``forward`` yields
``forward_kernel``.

.. code-block:: python

   design = Design("mm")
   design.set_dataroot("soda", __file__)
   with design.active_dataroot("soda"), design.active_fileset("soda"):
       design.set_topmodule("forward_kernel")
       design.add_file("mm.mlir")

   project = ASIC(design)
   project.add_fileset(["soda", "sdc"])
   freepdk45_demo(project)
   project.set_flow(SODAASICFlow())
   project.run()

Install the toolchain with ``sc-install mlir soda``, in that order:
``soda-opt`` links against MLIR's C++ libraries, so it can only be built against
the LLVM revision ``mlir`` installs.

:ref:`The SODA tutorial <soda_tutorial>` walks through the whole flow: the three
optimization strategies, each a flow of its own, and the knobs each one exposes.
