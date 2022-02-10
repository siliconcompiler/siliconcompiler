PDKs
===================================

Process Design Kits (PDKs) for leading process nodes generally include hundreds of files, documents, and configuration parameters, resulting in significant startup times in porting a design to a new node. The SiliconCompiler project minimizes per design PDK setup efforts by packaging PDKs as standardized reusable objects and making them available as named modules by the load_pdk() function. A complete set of supported open PDKs can be found in the :ref:`PDK Directory`. The table below shows the function interfaces supported in setting up PDKs.


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
     - chip
     - chip
     - load_pdk()
     - yes

   * - **make_docs**
     - Doc generator
     - None
     - chip
     - sphinx
     - yes


setup(chip)
-----------------

A minimally viable PDK will include a simulation device model and a set of codified manufacturing rules ("drc").
For an example setup, see the `Freepdk45 source code. <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/pdks/freepdk45.py>`_
The following Schema parameters are mandatory in setting up PDKs for SiliconCompiler.

::

    chip.set('mode', 'asic')
    chip.set('pdk','foundry', <foundry_name>)
    chip.set('pdk','process', <process_name>)
    chip.set('pdk','node', <node_geometry>)
    chip.set('pdk','version', <version>)
    chip.set('pdk','stackup', <stackuplist>)
    chip.set('pdk','drc',<tool>, <stackup>, 'runset', <file>)
    chip.set('pdk','lvs',<tool>, <stackup>, 'runset', <file>)
    chip.set('pdk','devmodel', <stackup>, <modeltype>, <tool>, <file>)

To support standard RTL2GDS flows, the PDK setup will also need to specify pointers to routing technology rules, layout abstractions, layer maps, and routing grids as shown in the below example. For a complete set of available PDK parameters, see the :ref:`Schema<SiliconCompiler Schema>`. ::

    chip.set('pdk','aprtech', <stackup>, <libtype>, 'lef', <file>)
    chip.set('pdk','layermap',<stackup>, 'def', 'gds', <file>)

    #Per layer grid setup
    chip.set('pdk','grid', <stackup>, <sc_name>, 'name',    <pdk_name>)
    chip.set('pdk','grid', <stackup>, <sc_name>, 'xoffset', 0.095)
    chip.set('pdk','grid', <stackup>, <sc_name>, 'xpitch',  0.19)
    chip.set('pdk','grid', <stackup>, <sc_name>, 'yoffset', 0.07)
    chip.set('pdk','grid', <stackup>, <sc_name>, 'ypitch',  0.14)
    chip.set('pdk','grid', <stackup>, <sc_name>, 'adj',     1.0)

Note that the 'techarg' dictionary in the schema can be used to pass named arguments to configure PDK setup.

make_docs()
-----------------
The make_docs() function is used by the projects auto-doc generation. The function should include a descriptive docstring and a call to the setup function to populate the schema with all settings:

  def make_docs():
    '''
    PDK description
    '''

    chip = siliconcompiler.Chip()
    setup(chip)

    return chip
