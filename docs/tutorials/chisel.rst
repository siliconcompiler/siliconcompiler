Chisel frontend
================

SiliconCompiler has a Chisel frontend that enables you to build Chisel designs for any supported SC target.  To get started using Chisel with SC, ensure that SC is installed following the directions from the :ref:`Installation` section, and install sbt from `here <https://www.scala-sbt.org/download.html>`_.

To build a Chisel design, the only things you need to do differently from a configuration perspective are:

1) Add all required Scala files as sources. Keep in mind that other frontend-specific features such as include or library directories are not yet supported for the Chisel frontend.
2) Set the 'frontend' parameter to 'chisel'.

Otherwise, you can configure the build as normal.

For example, to build the GCD example from the `Chisel project template repo <https://github.com/freechipsproject/chisel-template>`_, first copy the following code into a file called "GCD.scala".

.. code-block:: scala

    import chisel3._

    /**
      * Compute GCD using subtraction method.
      * Subtracts the smaller from the larger until register y is zero.
      * value in register x is then the GCD
      */
    class GCD extends Module {
      val io = IO(new Bundle {
        val value1        = Input(UInt(16.W))
        val value2        = Input(UInt(16.W))
        val loadingValues = Input(Bool())
        val outputGCD     = Output(UInt(16.W))
        val outputValid   = Output(Bool())
      })

      val x  = Reg(UInt())
      val y  = Reg(UInt())

      when(x > y) { x := x - y }
        .otherwise { y := y - x }

      when(io.loadingValues) {
        x := io.value1
        y := io.value2
      }

      io.outputGCD := x
      io.outputValid := y === 0.U
    }

.. note::

    SC's Chisel driver script selects the module to build based on the 'design'
    parameter.  You must ensure that top-level module's class name matches the
    'design' parameter you have set, and that this module does not include a
    ``package`` statement.

This design can then be quickly compiled to a GDS using the command line:

.. code-block:: bash

    sc GCD.scala -frontend chisel
    sc-show -design GCD

Or using Python::

    import siliconcompiler

    def main():
        chip = siliconcompiler.Chip()
        chip.set('source', 'GCD.scala')
        chip.set('frontend', 'chisel')
        chip.set('design', 'GCD')
        # default Chisel clock pin is 'clock'
        chip.clock(name='clock', pin='clock', period=5)
        chip.target('asicflow_freepdk45')
        chip.run()
        chip.summary()
        chip.show()

    if __name__ == '__main__':
        main()

For more information on creating designs using Chisel, see the `Chisel docs <https://www.chisel-lang.org/chisel3/docs/introduction.html>`_.
