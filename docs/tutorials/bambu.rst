C HLS frontend
======================

SiliconCompiler supports high-level synthesis of C code to any supported SC target, implemented using the Bambu HLS tool. To get started compiling C code with SC, ensure that SC is installed following the directions from the :ref:`Installation` section, and build Bambu from source following the instructions `here <https://panda.dei.polimi.it/?page_id=88>`_. For Ubuntu 20.04, we've additionally provided a `setup script <https://github.com/siliconcompiler/siliconcompiler/blob/main/setup/install-bambu.sh>`_.

To build a C design, the only things you need to do differently from a configuration perspective are:

1) Add all required C files as sources.
2) Set the 'frontend' parameter to 'c'.

Otherwise, you can configure the build as normal.

For example, to implement a GCD function as a circuit, first copy the following into a file called "gcd.c".

.. code-block:: c

  #include <stdio.h>

  short gcd(short a, short b) {
      // Implement GCD using the Euclidean Algorithm
      // https://www.khanacademy.org/computing/computer-science/cryptography/modarithmetic/a/the-euclidean-algorithm

      if (b > a) {
          short tmp = a;
          a = b;
          b = tmp;
      }

      while (a != 0 && b != 0) {
          short r = a % b;
          a = b;
          b = r;
      }

      if (a == 0)
          return b;
      else
          return a;
  }

  int main() {
      // Test the algorithm (will not get implemented as hardware).
      printf("gcd(4, 4) = %d\n", gcd(4, 4));
      printf("gcd(27, 36) = %d\n", gcd(27, 36));
      printf("gcd(270, 192) = %d\n", gcd(270, 192));

      return 0;
  }

.. note::

    SC's C frontend driver script selects a function to implement as a Verilog
    module using the 'design' parameter. Ensure that your C code includes a
    function that matches the value stored in 'design'.

This design can then be quickly compiled to a GDS using the command line:

.. code-block:: bash

    sc gcd.c -frontend c
    sc-show -design gcd

Or using Python::

    import siliconcompiler

    def main():
        chip = siliconcompiler.Chip()
        chip.set('source', 'gcd.c')
        chip.set('frontend', 'c')
        chip.set('design', 'gcd')
        # default Bambu clock pin is 'clock'
        chip.clock(name='clock', pin='clock', period=5)
        chip.load_target('freepdk45_demo')
        chip.run()
        chip.summary()
        chip.show()

    if __name__ == '__main__':
        main()

For more information on the Bambu project used for implementing this frontend, see their `docs <https://panda.dei.polimi.it/?page_id=31>`_.
