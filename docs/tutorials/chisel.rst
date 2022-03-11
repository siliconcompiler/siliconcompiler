Chisel frontend
================

SiliconCompiler has a Chisel frontend that enables you to build Chisel designs for any supported SC target.  To get started using Chisel with SC, ensure that SC is installed following the directions from the :ref:`Installation` section, and install sbt from `here <https://www.scala-sbt.org/download.html>`_.

To build a Chisel design, the only things you need to do differently from a configuration perspective are:

1) Add all required Scala files as sources. Keep in mind that other frontend-specific features such as include or library directories are not yet supported for the Chisel frontend.
2) Set the 'frontend' parameter to 'chisel'.

Otherwise, you can configure the build as normal.

For example, to build the GCD example from the `Chisel project template repo <https://github.com/freechipsproject/chisel-template>`_, first copy the following code into a file called "GCD.scala".

.. literalinclude:: examples/gcd_chisel/GCD.scala
  :language: scala

.. note::

    SC's Chisel driver script selects the module to build based on the 'design'
    parameter.  You must ensure that top-level module's class name matches the
    'design' parameter you have set, and that this module does not include a
    ``package`` statement.

This design can then be quickly compiled to a GDS using the command line:

.. literalinclude:: examples/gcd_chisel/run.sh
  :language: bash

Or using Python:

.. literalinclude:: examples/gcd_chisel/gcd_chisel.py

For more information on creating designs using Chisel, see the `Chisel docs <https://www.chisel-lang.org/chisel3/docs/introduction.html>`_.
