Contributing targets
=====================

The SiliconCompiler project was designed to encourage contribution. Theoretically, the project could support 100's of process PDKs, 100's of tools, and countless flows, but the project maintainers couldn't possibly manage all of them without community help.

.. note::

   Before making a PR, make sure you have the right to do so and you are not violating any potential NDAs and copyright law. In general, PDK targets should only be published by foundries and tool targets should only be published by the tool owners.

The process for target contributions is as follows:

1.) Clone the SiliconCompiler project from the `GitHub Repository <https://github.com/siliconcompiler/siliconcompiler>`_ and follow the :ref:`Installation` instructions.

2.) Create a flow, pdk, or tool target using the existing targets as guides. Place the target file in the appropriate location per the directory structure shown below:

.. code-block:: text

   .
   ├── flows
   │   ├── asicflow.py
   │   ├── dvflow.py
   │   └── fpgaflow.py
   ├── pdks
   │   ├── asap7.py
   │   ├── freepdk45.py
   │   ├── lambda.py
   │   └── skywater130.py
   └── tools
       ├── klayout
       │   ├── klayout.py
       │   └── ...
       ├── openroad
       │   ├── openroad.py
       │   ├── sc_apr.tcl
       │   └── ...
       ├── verilator
       │   └── verilator.py
       ├── yosys
       |    ├── yosys.py
       |    ├── sc_syn.tcl
       |    └── ...
       └── <...>

3.) Test the new target by calling it using the appropriate "load" function. For example. ::

  chip.load_pdk('<newpdk>')

4.) Read the `CONTRIBUTING <https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md>`_ guide to learn how to submit a PR.
