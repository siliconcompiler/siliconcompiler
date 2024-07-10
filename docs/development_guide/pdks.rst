PDKs
=====

Process Design Kits (PDKs) for leading process nodes generally include hundreds of files, documents, and configuration parameters, resulting in significant startup times in porting a design to a new node. The SiliconCompiler project minimizes per design PDK setup efforts by offering a way to package PDKs as standardized reusable objects, and making them available as named modules which can be loaded by the :meth:`.use()` function.

A complete set of supported open PDKs can be found in `pdks <pdks>`. The table below shows the function interfaces supported in setting up PDKs.

setup(chip)
-----------------

A minimally viable PDK will include a simulation device model and a set of codified manufacturing rules ("drc").
For an example setup, see the `Freepdk45 source code. <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/pdks/freepdk45.py>`_
An example of some of the fundamental settings are shown below.

::

    process = '<process_name>'
    chip.set('pdk', process, 'foundry', <foundry_name>)
    chip.set('pdk', process, 'node', <node_geometry>)
    chip.set('pdk', process, 'version', <version>)
    chip.set('pdk', process, 'stackup', <stackuplist>)
    chip.set('pdk', process, 'drc', 'runset', <tool>, <stackup>, <runset_type>, <file>)
    chip.set('pdk', process, 'lvs', 'runset', <tool>, <stackup>, <runset_type> <file>)
    chip.set('pdk', process, 'devmodel', <tool>, <modeltype>, <stackup>, <file>)

To support standard RTL2GDS flows, the PDK setup will also need to specify pointers to routing technology rules, layout abstractions, layer maps, and routing grids as shown in the below example. For a complete set of available PDK parameters, see the :keypath:`pdk` section of the :ref:`Schema <SiliconCompiler Schema>`. ::

    chip.set('pdk', process, 'aprtech', <tool>, <stackup>, <libtype>, 'lef', <file>)
    chip.set('pdk', process, 'layermap', <tool>, 'def', 'gds', <stackup>, <file>)

make_docs()
-----------------
The ``make_docs()`` function is used by the projects auto-doc generation. The function should include a descriptive docstring and a call to the setup function to populate the schema with all settings::

  def make_docs(chip):
    '''
    PDK description
    '''

    setup(chip)
    return chip

PDK Modules
-----------

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

   * - **setup**
     - PDK setup function
     - :class:`.Chip`
     - :class:`siliconcompiler.PDK`
     - :meth:`.use()`
     - yes

   * - **make_docs**
     - Doc generator
     - :class:`.Chip`
     - :class:`siliconcompiler.PDK`
     - sphinx
     - no
