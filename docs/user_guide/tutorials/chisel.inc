.. _chisel_frontend:

Chisel frontend
---------------

SiliconCompiler has a :ref:`Chisel <tool-chisel>` frontend that enables you to build Chisel designs for any supported SC target.
To get started using Chisel with SC, ensure that SC is installed following the directions from the :ref:`Installation <installation>` section, and `install sbt <https://www.scala-sbt.org/download.html>`_.
See for links to helpful build :ref:`scripts <External Tools>`.

To build a Chisel design, the only thing you need to do differently from a configuration perspective is:
Add all required Scala files as sources.
Keep in mind that other frontend-specific features such as include or library directories are not yet supported for the Chisel frontend.

Otherwise, you can configure the build as normal.

For example, to build the GCD example from the `Chisel project template repo <https://github.com/chipsalliance/chisel-template>`_, first copy the following code into a file called "GCD.scala".

.. literalinclude:: examples/gcd/GCD.scala
   :language: scala
   :caption: examples/gcd/GCD.scala

This design can then be quickly compiled to a GDS using Python:

.. literalinclude:: examples/gcd/gcd_chisel.py
   :language: python
   :caption: examples/gcd/gcd_chisel.py

For more information on creating designs using Chisel, see the `Chisel docs <https://www.chisel-lang.org/docs>`_.
