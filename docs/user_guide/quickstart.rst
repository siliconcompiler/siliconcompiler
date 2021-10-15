Quickstart quide
===================================

This section serves as a quick demonstration of the SiliconCompiler infrastructure.
The guide assumes the SiliconCompiler Python package has been installed already. For installation
instructions, see the :ref:`installation<Installation>` section of the user guide.


First, let's create a simple design. Copy paste the code for binary adder implementation below and
save to a file called 'add.v'. (you will need to remember where you saved this file later to
ensure that SC can find the file.) To keep things simple, for the quickstart exaxmple, we recommend
running SC out of the same directory/folder as 'add.v'

.. code-block:: verilog

   module add
   #(parameter N    = 32
   )
   (//inputs
   input [N-1:0]  a, // first operand
   input [N-1:0]  b, // second operand
   input 	  cin,// carry in
   //outputs
   output [N-1:0] sum,// sum
   output 	  cout// carry out from msb
   );

   assign {cout,sum[N-1:0]} = a[N-1:0] + b[N-1:0] + cin;

   endmodule

Next, copy the SiliconCompiler setup program below and save it as 'add.py' (making sure you don't
mess up the indentation). The code tells SC to compile the add verilog module using an asicflow in the
virtual 'freepdk45' PDK.::

  import siliconcompiler
  chip = siliconcompiler.Chip()
  chip.set('source', 'add.v')
  chip.set('design', 'add')
  chip.target('asicflow_freepdk45')

`verilator.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/tools/verilator/verilator.py>`_

To run SiliconCompiler remotely, visit `beta.siliconcompiler.com <https://beta.siliconcompiler.com>`
to set up an account with your work or university email address. You will then be emailed a public key
and instructions for how to save the key. Copy paste the following code into your 'add.py' compilation
file, replacing the content inside <> with the information from the beta signup. These commands should
be omitted for local execution.::

  chip.set('remote_addr', 'https://server.siliconcompiler.com')
  chip.set('remote_user', '<signup email>')
  chip.set('remote_key', '<beta keyfile>')

To run compilation on your local machine, you will need to see the installation instructions fore each tool (yosys, openroad, etc) before proceeding. Links to all tools can be found in the :ref:`tools<Tools directory>`.

All that is left is now to add a required run() command to compile the design. For good measure, we
also added a command for generating a table based text summary of the run metrics::

  chip.run()
  chip.summary()

Save the file again and run it (either from the comamnd line or from inside an IDE).

.. code-block:: console

   $ python add.py

A successful run should look something like the excerpt below.

.. code-block:: console



To view the layout produced by SiliconCompiler, you will need to install a GDS
viewer. We recommand the excellent open source multi-platform program 'klayout'.
Once you have installed klayout, you can view the 'add' layout with the following
command. The sc-show is a SiliconCompiler app that loads the run manfiest to make
sure all the technology files are set up correctly, and then loads the layout
file to view.

.. code-block:: console

   | $ sh-show build/add/job0/export/0/outputs/add.gds -cfg build/add/job0/export/0/outputs/add.pkg.json
