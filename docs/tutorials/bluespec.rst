Bluespec frontend
===================

SiliconCompiler has a Bluespec frontend that enables you to build Bluespec designs for any supported SC target.  To get started using Bluespec with SC, ensure that SC is installed following the directions from the :ref:`Installation` section, and download bsc or install it from source following the directions `here <https://github.com/B-Lang-org/bsc#download>`_. For Ubuntu 20.04, we've additionally provided a `setup script <https://github.com/siliconcompiler/siliconcompiler/blob/main/setup/install-bsc.sh>`_ to build it from source automatically.

To build a Bluespec design, the only things you need to do differently from a configuration perspective are:

1) Add the Bluespec top-level package as a 'source', and add all directories containing imported modules as entries in 'ydir'. Keep in mind that the Bluespec integration only supports specifying a single top-level source file, so you must use 'ydir' for all other sources.
2) Set the 'frontend' parameter to 'bluespec'.

Otherwise, you can configure the build as normal.

For example, to build this fibonacci example adapted from the `bsc smoke test <https://github.com/B-Lang-org/bsc/blob/main/examples/smoke_test/FibOne.bsv>`_, first copy the following code into a file called "FibOne.bsv".

.. code-block:: systemverilog

  interface FibOne_IFC;
     method Action nextFib;
     method ActionValue #(int)  getFib;
  endinterface

  (* synthesize *)
  module mkFibOne(FibOne_IFC);
     // register containing the current Fibonacci value
     Reg#(int) this_fib <- mkReg (0);
     Reg#(int) next_fib <- mkReg (1);

     method Action nextFib;
        this_fib <= next_fib;
        next_fib <= this_fib + next_fib;  // note that this uses stale this_fib
    endmethod

    method ActionValue#(int) getFib;
      return this_fib;
    endmethod

  endmodule: mkFibOne

.. note::

    SC's Bluespec driver script selects the module to build based on the
    'design' parameter. You must ensure that the single file passed in via the
    'source' parameter contains a module name that matches the value in 'design'.

This design can then be quickly compiled to a GDS using the command line:

.. code-block:: bash

    sc FibOne.bsv -design mkFibOne -frontend bluespec
    sc-show -design mkFibOne

Or using Python::

    import siliconcompiler

    def main():
        chip = siliconcompiler.Chip()
        chip.set('source', 'FibOne.bsv')
        chip.set('frontend', 'bluespec')
        chip.set('design', 'mkFibOne')
        # default Bluespec clock pin is 'CLK'
        chip.clock(name='clock', pin='CLK', period=5)
        chip.target('asicflow_freepdk45')
        chip.run()
        chip.summary()
        chip.show()

    if __name__ == '__main__':
        main()

For more information on creating designs using Bluespec, see the `Bluespec docs <https://github.com/B-Lang-org/bsc#documentation>`_.
