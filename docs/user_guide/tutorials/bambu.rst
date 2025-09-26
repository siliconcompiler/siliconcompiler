C HLS frontend
-----------------

SiliconCompiler supports high-level synthesis of C code to any supported SC target, implemented using the :ref:`Bambu <bambu>` HLS tool.
To get started compiling C code with SC, ensure that SC is installed following the directions from the :ref:`Installation` section, and `build Bambu from source <https://panda.dei.polimi.it/?page_id=88>`_.
See for links to helpful build :ref:`scripts <External Tools>`.

To build a C design, the only thing you need to do differently from a configuration perspective is:
Add all required C files as inputs.

Otherwise, you can configure the build as normal.

For example, to implement a GCD function as a circuit, first copy the following into a file called "gcd.c".

.. literalinclude:: examples/gcd/gcd.c
   :language: c
   :caption: examples/gcd/gcd.c

This design can then be quickly compiled to a GDS using Python:

.. literalinclude:: examples/gcd/gcd_hls.py
   :language: python
   :caption: examples/gcd/gcd_hls.py

For more information on the Bambu project used for implementing this frontend, see their `docs <https://panda.dei.polimi.it/?page_id=31>`_.
