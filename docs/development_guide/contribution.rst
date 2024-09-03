Contributing modules
=====================

The SiliconCompiler project was designed to encourage contribution.
Theoretically, the project could support 100's of process PDKs, 100's of tools, and countless flows, but the project maintainers couldn't possibly manage all of them without community help.

.. note::

   Before making a pull request, make sure you have the right to do so and you are not violating any potential `NDAs <https://en.wikipedia.org/wiki/Non-disclosure_agreement>`_ and `copyright <https://en.wikipedia.org/wiki/Copyright>`_ law.
   In general, PDK modules should only be published by foundries and tool modules should only be published by the tool owners.

The process for target contributions is as follows:

1. Clone the SiliconCompiler project from the `GitHub Repository <https://github.com/siliconcompiler/siliconcompiler>`_ and follow the :ref:`Installation` instructions.

2. Create a :ref:`flow <flows>`, :ref:`pdk <pdks>`, :ref:`library <libraries>`, :ref:`target <targets>`, or :ref:`tool <tools>` using the existing modules as guides.
   Place the module file in the appropriate location per the directory structure shown below:

.. code-block:: text

   .
   ├── flows
   │   ├── asicflow.py
   │   ├── dvflow.py
   │   └── fpgaflow.py
   │   └── ...
   ├── libs
   │   ├── asap7sc7p5t.py
   │   ├── nangate45.py
   │   └── sky130hd.py
   │   └── ...
   ├── pdks
   │   ├── asap7.py
   │   ├── freepdk45.py
   │   └── skywater130.py
   │   └── ...
   ├── targets
   │   ├── asap7_demo.py
   │   ├── freepdk45_demo.py
   │   └── skywater130_demo.py
   │   └── ...
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
       |    ├── yosys.py
       |    ├── sc_syn.tcl
       |    └── ...
       └── <...>

3. Test the new target by calling :meth:`.use()`.

.. code-block:: python

  import <newpdk>
  chip.use(<newpdk>)

4. Read the `contributing <https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md>`_ guide to learn how to submit a pull request.
