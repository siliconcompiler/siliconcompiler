Environment Variables
========================

This section describes the environment variables used by SiliconCompiler to control
execution and file access.

.. option:: SCPATH

   Specifies path(s) to a user specified directory to be added to the SC search
   path for loading named targets by the target() method. The path(s) provided
   must point to the root of a a directory structure that mimics the built-in SC
   setup structure shown below.

.. code-block:: text

   .
   ├── flows
   │   ├── asicflow.py
   │   ├── dvflow.py
   │   └── fpgaflow.py
   ├── foundries
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
