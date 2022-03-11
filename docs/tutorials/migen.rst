Python-based frontends
===========================

Since SC itself is a Python library, it can be used as-is in an end-to-end build script with any Python-based HDL that can be scripted to export designs to Verilog.

For example, if you have SC installed already, you can quickly get started building designs written in the Migen HDL. To install Migen, run ``pip install migen``. Then, paste the following into a file called "migen_heartbeat.py".

.. literalinclude:: examples/migen_heartbeat/migen_heartbeat.py

Run this file with ``python migen_heartbeat.py`` to compile your Migen design down to a GDS and automatically display it in KLayout.

In this example, the ``Heartbeat`` class describes a design as a Migen module, and the ``main()`` function implements the build flow. The flow begins by using Migen's built-in functionality for exporting the design as a file named "heartbeat.v". The rest of the flow uses SC's core API to take this Verilog file and feed it into a basic asicflow build, as described in the :ref:`Quickstart guide`. For more info on how Migen works, see the `Migen docs <https://m-labs.hk/migen/manual/>`_.

Although we wrote this example using Migen in particular, the concepts apply to other Python-based HDLs, such as `MyHDL  <https://www.myhdl.org/>`_ or `Amaranth <https://github.com/amaranth-lang/amaranth>`_ (note that Amaranth's Verilog backend requires Yosys installed locally).
