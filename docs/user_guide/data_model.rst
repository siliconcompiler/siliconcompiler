Data model
===================================

The SiliconCompiler Schema is a data structure that stores all configurations and metrics gathered during the compilation process. Each schema entry ("parameter") is a self contained leaf cell with a required set of standardized key/value pairs ("fields"). The example below shows the definition of one of the parameters named 'design'.

.. code-block:: python

    scparam(cfg,['design'],
            sctype='str',
            scope='global',
            require='all',
            shorthelp="Design top module name",
            switch="-design <str>",
            example=["cli: -design hello_world",
                    "api: chip.set('design', 'hello_world')"],
            schelp="""Name of the top level module or library. Required for all
            chip objects.""")

The table below summarizes mandatory fields used in all parameter definitions.

.. list-table::
   :widths: 10 25 50
   :header-rows: 1

   * - Field
     - Description
     - Values

   * - **type**
     - Parameter type
     - file, dir, str, float, bool, int, [], (a,b)

   * - **defvalue**
     - Default schema value
     - Type dependent

   * - **shorthelp**
     - Short single line help string.
     - String

   * - **help**
     - Multi-line documentation string
     - String

   * - **example**
     - Usage examples for CLI ad API
     - String

   * - **lock**
     - Enable/disable for set()/add() methods
     - True / False

   * - **require**
     - Flow based use requirements
     - String

   * - **switch**
     - Mapping of parameter to a CLI switch
     - String

The file type parameters have the additional required fields show in the table below:

.. list-table::
   :widths: 10 25 50
   :header-rows: 1

   * - Field
     - Description
     - Legal Values

   * - **author**
     - File author
     - String

   * - **date**
     - File date stamp
     - String

   * - **signature**
     - Author signature key
     - String

   * - **filehash**
     - File hash value
     - String

   * - **hashalgo**
     - Hashing algorithm used
     - sha256,md5,...

   * - **copy**
     - Whether to copy files into build directory
     - True / False


Accessing schema parameters is done using the :meth:`.set()`, :meth:`.get()`, and :meth:`.add()` Python methods. The following shows how to create a chip object and manipulate a schema parameter in Python.

.. literalinclude:: examples/setget.py

Reading and writing the schema to and from disk is handled by the :meth:`.read_manifest()` and :meth:`.write_manifest()` Python API methods. Supported export file formats include TCL, JSON, and YAML. By default, only non-empty values are written to disk.

.. literalinclude:: examples/write_manifest.py

The JSON structure below shows the 'design' parameter exported by the :meth:`.write_manifest()`  method.

.. code-block:: json

    "design": {
        "defvalue": null,
        "example": [
            "cli: -design hello_world",
            "api: chip.set('design', 'hello_world')"
        ],
        "help": "Name of the top level module or library. Required for all\nchip objects.",
        "lock": "false",
        "notes": null,
        "require": "all",
        "scope": "global",
        "shorthelp": "Design top module name",
        "signature": null,
        "switch": "-design <str>",
        "type": "str",
        "value": "hello_world"
    },

To handle complex scenarios required by advanced PDKs, the Schema supports dynamic nested dictionaries. A 'default' keyword is used to define the dictionary structure during object creation. Populating the object dictionary with actual keys is done by the user during compilation setup. The example below illustrates how 'default' is used as a placeholder for the timing model filetype and corner. These dynamic dictionaries makes it easy to set up an arbitrary number of libraries and corners in a PDK using Python loops.

.. code-block:: python



    corner='default'
    padkname='default'
    tool='default'
    stackup='default'
    scparam(cfg, ['pdk', pdkname, 'pexmodel', tool, stackup, corner],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: parasitic TCAD models",
            switch="-pdk_pexmodel 'pdkname tool stackup corner <file>'",
            example=[
                "cli: -pdk_pexmodel 'asap7 fastcap M10 max wire.mod'",
                "api: chip.set('pdk','asap7','pexmodel','fastcap','M10','max','wire.mod')"],
            schelp="""
            List of filepaths to PDK wire TCAD models used during automated
            synthesis, APR, and signoff verification. Pexmodels are specified on
            a per metal stack basis. Corner values depend on the process being
            used, but typically include nomenclature such as min, max, nominal.
            For exact names, refer to the DRM. Pexmodels are generally not
            standardized and specified on a per tool basis. An example of pexmodel
            type is 'fastcap'.""")

The SiliconCompiler Schema is roughly divided into the following major sub-groups:

.. list-table::
   :widths: 10 10 50
   :header-rows: 1

   * - Group
     - Parameters
     - Description

   * - **option**
     - 47
     - Compilation options

   * - **tool**
     - 24
     - Individual tool settings

   * - **flowgraph**
     - 8
     - Execution flow definition

   * - **pdk**
     - 46
     - PDK related settings

   * - **asic**
     - 45
     - ASIC related settings

   * - **fpga**
     - 5
     - FPGA related settings

   * - **constraint**
     - 7
     - Advanced timing analysis settings

   * - **model**
     - 7
     - Models/abstractions of design

   * - **metric**
     - 40
     - Metric tracking

   * - **record**
     - 15
     - Compilation history tracking

   * - **package**
     - 28
     - Packaging manifest

   * - **datasheet**
     - 36
     - Design interface specifications

   * - **units**
     - 9
     - Global units

   * - **total**
     - 317
     -

Refer to the :ref:`Schema <SiliconCompiler Schema>` and :ref:`Python API<Core API>` sections of the reference manual for more information. Another good resource is the single file `Schema source code <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/schema.py>`_.
