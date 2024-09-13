.. _dev_libraries:

Libraries
=========

Efficient hardware and software development demands a robust ecosystem of reusable high quality components.
In SiliconCompiler, you can add new IP to your design by creating a :class:`.Library` object which can be passed into the :meth:`.use()` function.
The :class:`.Library` class contains its own Schema dictionary, which can describe a macro block or standard cell library.

The general flow to create and import a library is to instantiate a :class:`.Library` object, set up any required sources (in the case of a soft library), or models and outputs (in case of a hardened library), and then import it into a parent design :class:`.Chip` object.
To enable simple 'target' based access, it is recommended that fundamental physical foundry sponsored IP (stdcells, GPIO, memory macros) are set up as part of reusable library modules.
To select which standard cell libraries to use during compilation, add their names to the :keypath:`asic, logiclib` parameter, to select macro libraries, add their names to the :keypath:`asic, macrolib` parameter, and to select soft-IP libraries, add their names to the :keypath:`option, library` parameter.

Functions
---------

The table below shows the function interfaces for setting up Library objects.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Args
     - Returns
     - Used by
     - Required

   * - :ref:`setup() <library_setup>`
     - Library setup function
     - optional keyword arguments
     - :class:`.Library` or list of :class:`.Library`
     - :meth:`.use()`
     - yes

   * - :ref:`make_docs() <library_make_docs>`
     - Doc generator
     - :class:`.Chip`
     - :class:`.Library`
     - sphinx
     - no

.. _library_setup:

setup()
-------

A library can be setup as either a :ref:`foundational IP <library_setup_foundation>` library, such as those for foundry sponsored IP, or a :ref:`soft library <library_setup_soft>`, which can be used to include external IP in your design.

.. _library_setup_foundation:

Foundational IP
***************

Here is an example of setting up a :class:`.Library` object with a hard IP macro.

.. code-block:: python

  from siliconcompiler import Library

  lib = Library('mymacro', package='mypackage')
  lib.register_source('mypackage', path='git+https://github.com/myproject/mypackage', ref='v1.0')
  lib.add('output', '10M', 'lef', 'mymacro.lef')
  lib.add('output', '10M', 'gds', 'mymacro.gds')

  return lib

This example creates a library named ``mymacro`` which contains two files a lef and gds.
These files are included in the ``mypackage``, which was defined using :meth:`.register_source()`.
In this case it is defined as a reference to a github repository, for IPs with liberty files and GDSs, it is recommended that the distribution be via tagged releases.


.. _library_setup_soft:

Soft IP
*******

Here is an example of setting up a :class:`.Library` object with a HDL IP.

.. code-block:: python

  from siliconcompiler import Library
  from hdlpackage import subcompnent

  lib = Library('mymacro', package='mypackage', auto_enable=True)
  lib.register_source('mypackage', path='python://hdlpackage')
  lib.input('mymacro.v')
  lib.input('mymacro_submodule.v')
  lib.add('option', 'idir', 'include')

  lib.use(subcompnent)

  return lib

This example creates a library named ``mymacro`` which contains two source files and a include directory.
These files are included in the ``mypackage``, which was defined using :meth:`.register_source()`.
In this case, the files are bundled with the python package as HDL tends to be fairly small and this can be easily distributed via `pypi.org <https://pypi.org/>`__.
The library also contains a reference to a ``subcompnent`` which is needed to compile this object.
Additionally, the ``auto_enable`` is set to ``True`` which ensures that when this library is brought in with :meth:`.use()` it is automatically added to the :keypath:`option, library`.


.. _library_make_docs:

make_docs(chip)
---------------
The ``make_docs()`` function is used by the projects auto-doc generation.
This function is only needed if the library requires additional inputs to be setup correctly.
The function should include a call to the setup function to populate the schema with all settings as shown below.
The input to this function ``chip`` is a chip object created by the auto-doc generator.

.. code-block:: python

  def make_docs(chip):
    return setup()
