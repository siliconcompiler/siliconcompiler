.. _examples:

################
Example Designs
################

Every directory below is a working, tested design in the
`examples <https://github.com/siliconcompiler/siliconcompiler/tree/main/examples>`__
folder of the repository. They run in CI, so they compile against the current
release rather than the one they were written for.

This page is generated from those directories. A new example appears here by
existing -- there is no list to keep in step.

Running one
===========

Clone the repository, or find the folder inside your installed package, and run
the script named as the entry point:

.. code-block:: bash

   git clone https://github.com/siliconcompiler/siliconcompiler.git
   cd siliconcompiler/examples/gcd
   python gcd.py

Where the entry point is ``make.py``, it holds several targets rather than one
script body, and :ref:`smake <howto_smake>` runs them by name:

.. code-block:: bash

   cd siliconcompiler/examples/heartbeat
   smake --help          # what this example can do
   smake lint            # run one of them

**Read "Requires" before starting a run.** Most examples need EDA tools
installed locally -- see :ref:`External Tools <external_tools>`, or use
:ref:`Docker <docker>` to run them without installing anything. The ones marked
*no PDK* are the cheapest place to start.

Where to start
==============

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - If you want to
     - Start with
   * - Run something in seconds, with no :term:`PDK`
     - :ref:`adder_cocotb <example-adder_cocotb>` (simulation),
       :ref:`sva_sby <example-sva_sby>` (formal),
       :ref:`blinky <example-blinky>` (FPGA)
   * - See a plain RTL-to-GDSII build
     - :ref:`gcd <example-gcd>`, then :ref:`aes <example-aes>` for something
       larger
   * - Compile from something other than Verilog
     - :ref:`fibone <example-fibone>` (Bluespec),
       :ref:`ghdl_fsynopsys <example-ghdl_fsynopsys>` (VHDL),
       :ref:`heartbeat_migen <example-heartbeat_migen>` (Migen),
       :ref:`mlir_hls <example-mlir_hls>` (LLVM IR)
   * - Build a design out of other designs
     - :ref:`picorv32 <example-picorv32>`,
       :ref:`macro_reuse <example-macro_reuse>`,
       :ref:`uniquify <example-uniquify>`
   * - Sweep, parallelise, or analyse a build
     - :ref:`parallel <example-parallel>`,
       :ref:`oh_experiments <example-oh_experiments>`,
       :ref:`pex_calibration <example-pex_calibration>`
   * - See every project type in one place
     - :ref:`heartbeat <example-heartbeat>`

All examples
============

.. scexamples:: ../../examples
