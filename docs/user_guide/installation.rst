Installation
===================================

To install the current release from PyPI.

.. code-block:: console

   $ pip install siliconcompiler


To install from the latest SiliconCompiler developer repository.

.. code-block:: console

   $ git clone https://github.com/siliconcompiler/siliconcompiler
   $ cd siliconcompiler
   $ pip install -r requirements.txt
   $ python -m pip install -e .

Verification
---------------------

To check the version of SC installed:

.. code-block:: console

  $ python -m pip show siliconcompiler

To verify the operation of SC, run the following sample code::

   import siliconcompiler
   chip = siliconcompiler.Chip()
   print(chip.get('scversion'))

The output should be the version number you expect to see, similar to below:


.. parsed-literal::

   \ |release|


Pre-requisites
---------------

For remote processing, you are now ready to go! No installationn required as long as the
tools are installed on the remote server.

For local execution, you will also need to install all the necesary external tools based
on the installation instructions referenced in the tools directory or the instructions provided by a
commercial EDA vendor.

Python dependencies
-------------------

SiliconCompiler relies on the following Python packages. Note that these will be
installed automatically when installing SC via pip, so there should be no need
to install them manually.

.. requirements::
