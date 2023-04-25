######################################
Data Model (aka The Schema)
######################################

SiliconCompiler uses a data structure class, called the Schema, to store all information associated with the compilation process and the design that's being compiled.

The types of information stored by the SiliconCompiler Schema include, but is not limited to:

- How the design is defined (i.e. HW architectural definitions)
- How the design is compiled (i.e. Build tools and technology specifics)
- How the design is optimized (i.e. Different tool options for  build experiments)

This data is stored in Schema parameters, and accessed through Schema methods.

.. image:: _images/schema_diagram.png
   :scale: 50%
..   :align: center
	   

The diagram above shows a few example Schema parameters and methods for an overview of how data is stored and accessed.

.. rst-class:: page-break

The following sections provide more detail on Schema parameters and methods.
  
Schema Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^

The Schema is "configured," or defined, based on its parameters. 

Major Parameter Categories
---------------------------
The SiliconCompiler Schema is divided into the following major sub-groups of parameters:

.. schema_group_summary::


Parameter Sub-tree Example
--------------------------

Some parameters have their own subtrees in order to be fully defined. The table below shows an example of a parameter, called :ref:`constraint`, which specifies the design constraints, from timing-specific parameters to physical design parameters.

.. schema_category_summary::
  :category: constraint

Accessing Schema Parameters
---------------------------

Accessing schema parameters is done using Python methods defined in :class:`Core API <siliconcompiler.core.Chip>`.

.. rst-class:: page-break

The following example shows how to create a chip object and manipulate the :ref:`input` schema parameter in Python by setting the parameter with the :meth:`.set()` method, accessing it with the :meth:`.get()` method, and adding to the parameter with the :meth:`.add()` method.

.. code-block:: python

   >>> import siliconcompiler
   >>> chip = siliconcompiler.Chip('fulladder')

   >>> chip.set('input', 'rtl', 'verilog', 'fulladder.v')
   >>> print(chip.get('input', 'rtl', 'verilog'))
   ['fulladder.v']

   >>> chip.add('input', 'rtl', 'verilog', 'halfadder.v')

   >>> print(chip.get('input', 'rtl', 'verilog'))
   ['fulladder.v', 'halfadder.v']


You can also use methods like :meth:`.input()`, a helper function used in the :ref:`define design` section of the :ref:`quickstart guide` to set a parameter. 

.. code-block:: python

   >>> chip.getkeys('input')
   ['rtl']
   >>> chip.set('input', 'constraint', 'sdc', 'fulladder.sdc')
   >>> print(chip.set('input', 'constraint', 'sdc'))
   
   >>> print(chip.get('input', 'constraint', 'sdc'))
   ['fulladder.sdc']
   
   >>> chip.getkeys('input')
   ['rtl', 'constraint']   
   
   
As you can see, additional methods like :meth:`.getkeys()` are helpful for checking your parameters. See :class:`siliconcompiler.core.Chip` for more infomration on methods which can be used to manipulate Schema parameters.


Manifest
^^^^^^^^^^^^^^^^^^^^^

The Schema is recorded to a :term:`manifest`. This file serves not only as a reference of all the design and compilation parameters, it also provides a mechanism to reload a design.

If you ran the :ref:`asic demo`, you should have a manifest written out to ::
  
  build/<design>/job0/<design>.pkg.json


The :meth:`.read_manifest()` and :meth:`.write_manifest()` Python API methods handle reading and writing the Schema to/from disk. Besides JSON, other supported export file formats include TCL, and YAML. By default, only non-empty values are written to disk.

.. literalinclude:: examples/write_manifest.py

The :meth:`.write_manifest()` method above writes out the JSON file below, showing the standardized key/value pairs ("fields") associated with the :ref:`design` parameter.

.. code-block:: json

    "design": {
        "defvalue": null,
        "lock": false,
        "node": {
            "global": {
                "global": {
                    "value": "hello_world"
                }
            }
        },
        "notes": null,
        "pernode": "never",
        "require": "all",
        "scope": "global",
        "shorthelp": "Design top module name",
        "signature": null,
        "switch": "-design <str>",
        "type": "str"
    },
  
      

Additional Schema Information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Refer to the :ref:`Schema <SiliconCompiler Schema>` and :ref:`Python API<Core API>` sections of the reference manual for more information. Another good resource is the schema configuration file `Schema source code <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/schema/schema_cfg.py>`_.

	     
