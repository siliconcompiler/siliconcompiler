Bluespec frontend
===================

SiliconCompiler has a Bluespec frontend that enables you to build Bluespec designs for any supported SC target.  To get started using Bluespec with SC, ensure that SC is installed following the directions from the :ref:`Installation` section, and download bsc or install it from source following the directions `here <https://github.com/B-Lang-org/bsc#download>`_. For Ubuntu 20.04, we've additionally provided a `setup script <https://github.com/siliconcompiler/siliconcompiler/blob/main/setup/install-bsc.sh>`_ to build it from source automatically.

To build a Bluespec design, the only things you need to do differently from a configuration perspective are:

1) Add the Bluespec top-level package as a 'source', and add all directories containing imported modules as entries in 'ydir'. Keep in mind that the Bluespec integration only supports specifying a single top-level source file, so you must use 'ydir' for all other sources.
2) Set the 'frontend' parameter to 'bluespec'.

Otherwise, you can configure the build as normal.

For example, to build this fibonacci example adapted from the `bsc smoke test <https://github.com/B-Lang-org/bsc/blob/main/examples/smoke_test/FibOne.bsv>`_, first copy the following code into a file called "FibOne.bsv".

.. literalinclude:: examples/fibone/FibOne.bsv
  :language: systemverilog

.. note::

    SC's Bluespec driver script selects the module to build based on the
    'design' parameter. You must ensure that the single file passed in via the
    'source' parameter contains a module name that matches the value in 'design'.

This design can then be quickly compiled to a GDS using the command line:

.. literalinclude:: examples/fibone/run.sh
  :language: bash

Or using Python:

.. literalinclude:: examples/fibone/fibone.py

For more information on creating designs using Bluespec, see the `Bluespec docs <https://github.com/B-Lang-org/bsc#documentation>`_.
