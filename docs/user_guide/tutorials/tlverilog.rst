TL-Verilog frontend (Sandpiper)
-------------------------------

SiliconCompiler has a TL-Verilog frontend that enables you to build TL-Verilog designs compiled by :ref:`sandpiper` for any supported SC target.  To get started using TL-Verilog with SC, ensure that Sandpiper-SaaS, a TL-Verilog compiler as a microservice using the below command

.. code-block:: bash

   pip install sandpiper-saas

To build a TL-Verilog design, the only things you need to do differently from a configuration perspective are:

1) Add the Tl-Verilog top-level file as an 'input'. Keep in mind that the TL-Verilog compiler only supports specifying a single top-level source file, so your design must be in a single .tlv file.
2) Set the :keypath:`option, frontend` parameter to 'tlv'.

Otherwise, you can configure the build as normal.

For example, to build this adder example adapted from the, first copy the following code into a file called "adder.tlv".

.. literalinclude:: examples/adder/adder.tlv
  :language: systemverilog

.. note::

    SC's TL-Verilog driver script selects the module to build based on the
    'design' parameter. You must ensure that the single file passed in via the
    'source' parameter contains a module name that matches the value in 'design'.

This design can then be quickly compiled to a GDS using the command line:

.. literalinclude:: examples/adder/run.sh
  :language: bash

Or using Python:

.. literalinclude:: examples/adder/adder.py

For more information on creating designs using Tl-Verilog, see the `Tl-Verilog docs <https://makerchip.com>`_.
