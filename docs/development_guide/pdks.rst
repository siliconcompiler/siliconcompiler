.. _dev_pdks:

PDKs
=====

Process Design Kits (PDKs) for leading process nodes generally include hundreds of files, documents, and configuration parameters, resulting in significant startup times in porting a design to a new node.
The SiliconCompiler project minimizes per design PDK setup efforts by offering a way to package PDKs as standardized reusable objects, and making them available as named modules which can be loaded by the :meth:`.use()` function.

A complete set of supported open PDKs can be found in :ref:`pdks <builtin_pdks>`. The table below shows the function interfaces supported in setting up PDKs.

Functions
---------

The table below shows the function interfaces for setting up PDK objects.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Arg
     - Returns
     - Used by
     - Required

   * - :ref:`setup() <pdk_setup>`
     - PDK setup function
     - optional keyword arguments
     - :class:`.PDK`
     - :meth:`.use()`
     - yes

   * - :ref:`make_docs() <pdk_make_docs>`
     - Doc generator
     - :class:`.Chip`
     - :class:`.PDK`
     - sphinx
     - no


.. _pdk_setup:

setup()
-------

A minimally viable PDK will include a simulation device model and a set of codified manufacturing rules ("drc").
For an example setup, see the `Freepdk45 source code <https://github.com/siliconcompiler/lambdapdk/blob/main/lambdapdk/freepdk45/__init__.py>`_.
An example of some of the fundamental settings are shown below.

.. code-block:: python

    from siliconcompiler import PDK
    process = '<process_name>'

    pdk = PDK(process)
    pdk.set('pdk', process, 'foundry', <foundry_name>)
    pdk.set('pdk', process, 'node', <node_geometry>)
    pdk.set('pdk', process, 'version', <version>)
    pdk.set('pdk', process, 'stackup', <stackuplist>)
    pdk.set('pdk', process, 'drc', 'runset', <tool>, <stackup>, <runset_type>, <file>)
    pdk.set('pdk', process, 'lvs', 'runset', <tool>, <stackup>, <runset_type> <file>)
    pdk.set('pdk', process, 'devmodel', <tool>, <modeltype>, <stackup>, <file>)

To support standard RTL2GDS flows, the PDK setup will also need to specify pointers to routing technology rules, layout abstractions, layer maps, and routing grids as shown in the below example.
For a complete set of available PDK parameters, see the :keypath:`pdk` section of the :ref:`Schema <SiliconCompiler Schema>`.

.. code-block:: python

    chip.set('pdk', process, 'aprtech', <tool>, <stackup>, <libtype>, 'lef', <file>)
    chip.set('pdk', process, 'layermap', <tool>, 'def', 'gds', <stackup>, <file>)


.. _pdk_make_docs:

make_docs(chip)
---------------
The ``make_docs()`` function is used by the projects auto-doc generation.
This function is only needed if the PDK requires additional inputs to be setup correctly.
The function should include a call to the setup function to populate the schema with all settings as shown below.
The input to this function ``chip`` is a chip object created by the auto-doc generator.

.. code-block:: python

  def make_docs(chip):
    return setup()
