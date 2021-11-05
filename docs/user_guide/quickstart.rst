Quickstart quide
===================================

The SiliconCompiler project is designed to support automated translation from a
broad set of high level languages into manufacturable and deployable hardware. In
this quickstart guide, we will illustrate an example of automated compilation by
translating a simple Verilog based design into a as GDSII IC layout database.

Design
-------
As a case study we will use the the simple "heartbeat" design shown below.
The heartbeat module is a free running counter that creates a single clock cycle
pulse ("heartbeat") every time the counter rolls over. Copy paste the code into your
favorite text editor (vim, emacs, atom, notepad,etc) and save it to disk as
"heartbeat.v".

.. literalinclude:: examples/heartbeat.v
   :language: verilog

Setup
-----------------

To run SiliconCompiler using , visit `beta.siliconcompiler.com <https://beta.siliconcompiler.com>`
to set up an account with your work or university email address. You will then be emailed a public key
and instructions for how to save the key. Copy paste the following code into your 'add.py' compilation
file, replacing the content inside <> with the information from the beta signup. These commands should
be omitted for local execution.

To run compilation on your local machine, you will need to see the installation instructions fore each tool (yosys, openroad, etc) before proceeding. Links to all tools can be found in the :ref:`tools<Tools directory>`.


.. literalinclude:: examples/heartbeat.py
   :linenos:

.. literalinclude:: examples/heartbeat_remote.py


Compilation
------------

Run your compilation program from within your virtual Python environment.



.. code-block:: bash

   (venv) $ python heartbeat.py


.. literalinclude:: examples/heartbeat.log


View layout
------------

If you have 'klayout' installed locally, you can view the heartbeat layout in all its glory
using the 'sc-show' app distributed with the SiliconCompiler project.

.. code-block:: bash
   (venv) sc-show build/heartbeat/job0/export/0/outputs/heartbeat.gds -cfg build/heartbeat/job0/export/0/outputs/heartbeat.pkg.json
