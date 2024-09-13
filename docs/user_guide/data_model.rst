.. _data_model:

######################################
Design and Compilation Data
######################################

SiliconCompiler uses a data structure object, called :class:`.Schema`, also referred to as "the schema" in subsequent docs, to store all information associated with the compilation process and the design that's being compiled.

The types of information stored by the schema include, but is not limited to:

- How the design is defined (i.e. HW architectural definitions)
- How the design is compiled (i.e. Build tools and technology specifics)
- How the design is optimized (i.e. Different tool options for build experiments)

This data is stored in Schema parameters, and accessed through Schema methods.

.. image:: _images/schema_diagram.png
   :scale: 50%
   :align: center

The diagram above shows a few examples of Schema parameters and methods for an overview of how data is stored and accessed.

.. rst-class:: page-break

The following sections provide more detail on how information in the schema is initialized and manipulated.

Schema Configuration
^^^^^^^^^^^^^^^^^^^^

The schema is "configured," or defined, based on its parameters.

Major Parameter Categories
---------------------------
The SiliconCompiler Schema is divided into the following major sub-groups of parameters:

.. schema_group_summary::


Parameter Sub-tree Example
--------------------------

Some parameters have their own subtrees in order to be fully defined.
The table below shows an example of a parameter, called :ref:`constraint`, which specifies the design constraints, from timing-specific parameters to physical design parameters.

.. schema_category_summary::
  :category: constraint

Accessing Schema Parameters
---------------------------

While all the design and compilation information are stored in the Schema object, this information is manipulated through a separate data structured called :class:`.Chip`.


.. _chip_obj:

The Chip Object
+++++++++++++++++++

This separate data structure is different from the :class:`.Schema` since it instantiates the Schema object and is used to define methods that manipulate the compilation process.

.. autoclass:: siliconcompiler.Chip
   :noindex:

Chip Creation and Schema Parameter Access
+++++++++++++++++++++++++++++++++++++++++++

.. currentmodule:: siliconcompiler

The following example shows how to create a chip object and manipulate the :ref:`input` schema parameter in Python by setting the parameter with the :meth:`Chip.set()` method, accessing it with the :meth:`Chip.get()` method, and appending to the parameter field with the :meth:`Chip.add()` method.

.. code-block:: python

   >>> import siliconcompiler
   >>> chip = siliconcompiler.Chip('fulladder')

   >>> chip.set('input', 'rtl', 'verilog', 'fulladder.v')
   >>> print(chip.get('input', 'rtl', 'verilog'))
   ['fulladder.v']

   >>> chip.add('input', 'rtl', 'verilog', 'halfadder.v')

   >>> print(chip.get('input', 'rtl', 'verilog'))
   ['fulladder.v', 'halfadder.v']


The :class:`.Chip` object provides many useful :ref:`helper functions <core api>`. For example, in the :ref:`quickstart guide <define design>` , the :meth:`Chip.input()` helper function was used to set the chip timing constraints file, a simpler call than using :meth:`Chip.set()`.

.. code-block:: python

   >>> chip.input('fulladder.sdc')
   | INFO    | fulladder.sdc inferred as constraint/sdc

   >>> print(chip.get('input', 'constraint', 'sdc'))
   ['fulladder.sdc']


:meth:`Chip.getkeys()` is another example of a useful function, provided by :ref:`the chip object <core api>`, for checking your parameters.

.. code-block:: python

   >>> chip.getkeys('input')
   ['rtl', 'constraint']

   >>> chip.getkeys('input', 'rtl')
   ['verilog']

   >>> chip.getkeys('input', 'constraint')
   ['sdc']

You can see from the example above that using the :meth:`Chip.getkeys()` function, you're able to query the subtree of the parameter called ``input``, where the parameter tree can be visually represented as: ::

    └── input
       ├── constraint
       │   └── sdc
       └── rtl
           └── verilog

If you further go one step further down, you'll see that ``verilog`` is a leaf parameter, so the :meth:`Chip.getkeys()` function returns its parameter fields.

.. code-block:: python

   >>> chip.getkeys('input', 'rtl', 'verilog')
   ['type', 'scope', 'require', 'lock', 'switch', 'shorthelp', 'example', 'help', 'notes', 'pernode', 'node', 'hashalgo', 'copy']


Parameter fields are standardized variables which help to define the parameter.
In the case below, you can see that :meth:`Chip.get()` can also be used to query parameter fields to provide more information about the parameters:

.. code-block:: python

   >>> chip.get('input', 'rtl', 'verilog', field='type')
   '[file]'

   >>> chip.get('input', 'rtl', 'verilog', field='example')
   ["cli: -input 'rtl verilog hello_world.v'", "api: chip.set(input, 'rtl','verilog','hello_world.v')"]


:meth:`getkeys` is just one useful helpfer function; see :ref:`core api` for more information on methods which can be used to manipulate Schema parameters.


Manifest
^^^^^^^^^^^^^^^^^^^^^

The Schema is recorded to a :term:`manifest`. This file serves not only as a reference of all the design and compilation parameters, it also provides a mechanism to reload a design.

If you ran the :ref:`asic demo`, you should have a manifest written out to ::

  build/<design>/job0/<design>.pkg.json

The :meth:`Chip.read_manifest()` and :meth:`Chip.write_manifest()` Python API methods handle reading and writing the Schema to/from disk.
Besides `JSON <https://en.wikipedia.org/wiki/JSON>`_, other supported export file formats include `Tcl <https://en.wikipedia.org/wiki/Tcl>`_, `YAML <https://en.wikipedia.org/wiki/YAML>`_, and `csv <https://en.wikipedia.org/wiki/Comma-separated_values>`_.

.. literalinclude:: examples/write_manifest.py

The :meth:`Chip.write_manifest()` method above writes out the JSON file below, showing the standardized key/value pairs ("fields") associated with the :ref:`design` parameter.

.. code-block:: json

    "design": {
        "lock": false,
        "node": {
            "default": {
               "default": {
                    "signature": null,
                    "value": null
               }
            },
            "global": {
                "global": {
                    "signature": null,
                    "value": "hello_world"
                }
            }
        },
        "notes": null,
        "pernode": "never",
        "require": "all",
        "scope": "global",
        "shorthelp": "Design top module name",
        "switch": [
            "-design <str>"
        ],
        "type": "str"
    },



Additional Schema Information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Refer to the :ref:`Schema <SiliconCompiler Schema>` and :ref:`Python API<Core API>` sections of the reference manual for more information.
Another good resource is the schema configuration file `Schema source code <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/schema/schema_cfg.py>`_.
