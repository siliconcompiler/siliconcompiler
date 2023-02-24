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

Table summarizing mandatory parameter type and value fields.

.. list-table::
   :widths: 10 25 50
   :header-rows: 1

   * - Field
     - Description
     - Values

   * - **type**
     - Parameter type
     - file, dir, str, float, bool, int, [], enum, tuple

   * - **enum**
     - List of legal strings for enum type
     - List of Strings

   * - **unit**
     - Implied unit for parameter value
     - String

   * - **defvalue**
     - Default schema value
     - Type dependent

   * - **node**
     - Dictionary of fields based on step & index keys
     - Dictionary

   * - **pernode**
     - Enables/disables setting of value on a per node basis
     - 'never', 'required', 'optional'

   * - **lock**
     - Enable/disable for set()/add() methods
     - True / False

   * - **scope**
     - Scope of parameter in schema
     - 'global', 'job'

   * - **require**
     - Flow based use requirements
     - String

   * - **switch**
     - Mapping of parameter to a CLI switch
     - String

   * - **shorthelp**
     - Short single line help string.
     - String

   * - **help**
     - Multi-line documentation string
     - String

   * - **example**
     - Usage examples for CLI and API
     - String

   * - **notes**
     - User entered 'notes'/'disclaimers' about value being set.
     - String

   * - **hashalgo**
     - Hashing algorithm used (files only)
     - sha256,md5,...

   * - **copy**
     - Whether to copy files into build directory (files only)
     - True / False

Each parameter's node dictionary may contain some or all of the following fields, and may be set on a per-step/index based on the parameter's 'pernode' setting. Within the 'node' dictionary, the reserved keyword 'global' is used to represent a setting that applies to all steps or indices.

.. list-table::
   :widths: 10 25 50
   :header-rows: 1

   * - Field
     - Description
     - Legal Values

   * - **value**
     - Parameter value
     - Type dependent

   * - **signature**
     - Author signature key
     - String or List of Strings, type dependent

   * - **author**
     - File author (files only)
     - String

   * - **date**
     - File date stamp (files only)
     - String

   * - **filehash**
     - File hash value (files only)
     - String

Accessing schema parameters is done using the :meth:`.set()`, :meth:`.get()`, and :meth:`.add()` Python methods. The following shows how to create a chip object and manipulate a schema parameter in Python.

.. literalinclude:: examples/setget.py

When accessing parameters with 'optional' or 'required' pernode settings, schema accessor methods accept `step` and `index` keyword arguments.
These arguments are optional when setting optional-pernode parameters, and when
accessing them the most specific match is returned. For required-pernode
parameters, these keyword arguments must always be supplied, and it is an error
to access them with a step and index that have not yet been set.

.. code-block:: python

  import siliconcompiler
  chip = siliconcompiler.Chip('hello_world')

  # optional
  chip.set('asic', 'logiclib', ['mylib_rvt'])
  chip.set('asic', 'logiclib', ['mylib_lvt'], step='place')

  chip.get('asic', 'logiclib', step='syn', index=0) # => ['mylib_rvt']
  chip.get('asic', 'logiclib', step='place', index=1) # => ['mylib_lvt']

  # required
  chip.set('metric', 'warnings', 3, step='syn', index=0)

  chip.get('metric', 'warnings', step='syn', index=0) # => 3
  chip.get('metric', 'warnings', step='place', index=0) # => error, not set!

Reading and writing the schema to and from disk is handled by the :meth:`.read_manifest()` and :meth:`.write_manifest()` Python API methods. Supported export file formats include TCL, JSON, and YAML. By default, only non-empty values are written to disk.

.. literalinclude:: examples/write_manifest.py

The JSON structure below shows the 'design' parameter exported by the :meth:`.write_manifest()`  method.

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

To handle complex scenarios required by advanced PDKs, the Schema supports dynamic nested dictionaries. A 'default' keyword is used to define the dictionary structure during object creation. Populating the object dictionary with actual keys is done by the user during compilation setup. The example below illustrates how 'default' is used as a placeholder for the timing model filetype and corner. These dynamic dictionaries makes it easy to set up an arbitrary number of libraries and corners in a PDK using Python loops.

.. code-block:: python

    corner='default'
    pdkname='default'
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
     - 30
     - Compilation options

   * - **tool**
     - 24
     - Individual tool settings

   * - **flowgraph**
     - 10
     - Execution flow definition

   * - **pdk**
     - 42
     - PDK related settings

   * - **asic**
     - 20
     - ASIC related settings

   * - **fpga**
     - 6
     - FPGA related settings

   * - **constraint**
     - 33
     - Advanced timing analysis settings

   * - **metric**
     - 45
     - Metric tracking

   * - **record**
     - 18
     - Compilation history tracking

   * - **package**
     - 31
     - Packaging manifest

   * - **datasheet**
     - 41
     - Design interface specifications

   * - **units**
     - 9
     - Global units

   * - **total**
     - 350
     -

Refer to the :ref:`Schema <SiliconCompiler Schema>` and :ref:`Python API<Core API>` sections of the reference manual for more information. Another good resource is the schema configuration file `Schema source code <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/schema/schema_cfg.py>`_.
