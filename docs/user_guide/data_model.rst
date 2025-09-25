.. _data_model:

######################################
Design and Compilation Data
######################################

SiliconCompiler uses a data structure object, called the schema, to store all information associated with the compilation process and the design that's being compiled.

The types of information stored by the schema include, but is not limited to:

- How the design is defined (i.e. HW architectural definitions)
- How the design is compiled (i.e. Build tools and technology specifics)
- How the design is optimized (i.e. Different tool options for build experiments)

This data is stored in Schema parameters, and accessed through Schema methods.

.. image:: _images/schema_diagram.png
   :scale: 50%
   :align: center

The diagram above shows a few examples of Schema parameters and methods for an overview of how data is stored and accessed.

The following sections provide more detail on how information in the schema is initialized and manipulated.

Schema Configuration
^^^^^^^^^^^^^^^^^^^^

The schema is "configured," or defined, based on its parameters. These are documented in detail :ref:`in the schema reference <schema>`

Accessing Schema Parameters
---------------------------

All design and compilation information is stored in Schema objects, which you manipulate through the :class:`.BaseSchema` class.

The Schema Object
+++++++++++++++++

Project Creation and Schema Parameter Access
++++++++++++++++++++++++++++++++++++++++++++

.. currentmodule:: siliconcompiler.schema

The following example shows how to create a project object and manipulate the :keypath:`option,fileset` schema parameter in Python by setting the parameter with the :meth:`.BaseSchema.set()` method, accessing it with the :meth:`.BaseSchema.get()` method, and appending to the parameter field with the :meth:`.BaseSchema.add()` method.

.. code-block:: python

   >>> from siliconcompiler import Project
   >>> project = Project()

   >>> project.set('option', 'fileset', 'rtl')
   >>> print(project.get('option', 'fileset'))
   ['rtl']

   >>> project.add('option', 'fileset', 'sdc')
   >>> print(project.get('option', 'fileset'))
   ['rtl', 'sdc']

Manifest
^^^^^^^^

The Schema is recorded to a :term:`manifest`. This file serves not only as a reference of all the design and compilation parameters, it also provides a mechanism to reload a design.

If you ran the :ref:`asic demo`, you should have a manifest written out to ::

  build/<design>/job0/<design>.pkg.json

The :meth:`.BaseSchema.read_manifest()` and :meth:`.BaseSchema.write_manifest()` Python API methods handle reading and writing the Schema to/from disk.
Besides `JSON <https://en.wikipedia.org/wiki/JSON>`_, other supported export file formats include `Tcl <https://en.wikipedia.org/wiki/Tcl>`_, `YAML <https://en.wikipedia.org/wiki/YAML>`_, and `csv <https://en.wikipedia.org/wiki/Comma-separated_values>`_.

.. code-block:: python

   >>> from siliconcompiler import Project
   >>> project = Project()

   >>> project.write_manifest('manifest.json')

The :meth:`.BaseSchema.write_manifest()` method above writes out the JSON file below, showing the standardized key/value pairs ("fields") associated with the :keypath:`option,design` parameter.

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Refer to the :ref:`Schema <SiliconCompiler Schema>` and :ref:`Python API<schema_api>` sections of the reference manual for more information.
