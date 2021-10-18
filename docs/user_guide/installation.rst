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


Python dependencies
-------------------

SiliconCompiler relies on the following Python packages. Note that these will be
installed automatically when installing SC via pip, so there should be no need
to install them manually.

.. requirements::

Pre-requisites
---------------

SiliconCompiler relies on a number of external tools and projects. Supporting the multi-platform
installation of those tools is beyond the scope of the project, but we have included easy access
links to installation instructions in the reference manual :ref:`tools<Tools directory>` section.

Note that you can bypass the installation process using the remote processing workflow if you have
access to a server where the tools are pre-installed. See the :ref:`Quickstart guide<Quickstart guide>` for more details.
