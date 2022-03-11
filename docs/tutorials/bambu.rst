C HLS frontend
======================

SiliconCompiler supports high-level synthesis of C code to any supported SC target, implemented using the Bambu HLS tool. To get started compiling C code with SC, ensure that SC is installed following the directions from the :ref:`Installation` section, and build Bambu from source following the instructions `here <https://panda.dei.polimi.it/?page_id=88>`_. For Ubuntu 20.04, we've additionally provided a `setup script <https://github.com/siliconcompiler/siliconcompiler/blob/main/setup/install-bambu.sh>`_.

To build a C design, the only things you need to do differently from a configuration perspective are:

1) Add all required C files as sources.
2) Set the 'frontend' parameter to 'c'.

Otherwise, you can configure the build as normal.

For example, to implement a GCD function as a circuit, first copy the following into a file called "gcd.c".

.. literalinclude:: examples/gcd_hls/gcd.c
    :language: c

.. note::

    SC's C frontend driver script selects a function to implement as a Verilog
    module using the 'design' parameter. Ensure that your C code includes a
    function that matches the value stored in 'design'.

This design can then be quickly compiled to a GDS using the command line:

.. literalinclude:: examples/gcd_hls/run.sh
    :language: bash

Or using Python:

.. literalinclude:: examples/gcd_hls/gcd_hls.py

For more information on the Bambu project used for implementing this frontend, see their `docs <https://panda.dei.polimi.it/?page_id=31>`_.
