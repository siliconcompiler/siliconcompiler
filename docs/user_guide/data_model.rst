Data model
===================================

The SiliconCompiler Schema is a data structure that stores all configurations  and metrics  gathered during the compilation process. Each schema entry ("parameter") is a self contained leaf cell with a required set of standardized key/value pairs ("fields"). The example below shows the definition of one of the parameters named 'design'.

.. code-block:: python

   cfg['design'] = {
        'switch': "-design <str>",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Design top module name',
        'example': ["cli: -design hello_world",
                    "api: chip.set('design', 'hello_world')"],
        'help': """
        Name of the top level module to compile. Required for all designs with
        more than one module.
        """
    }

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


Accessing schema parameters is done using the set(), get(), and add() Python methods. The following shows how to create a chip object and manipulating a schema parameter in Python.

.. literalinclude:: examples/datamodel_setget.py

Reading and writing the schema to and from disk is handled by the read_manifest() and write_manifest() Python API methods. Supported export file formats include TCL, JSON, and YAML. By default, only non-empty values are written to disk.

.. literalinclude:: examples/datamodel_manifest.py

The JSON structure below shows the 'design' parameter exported by the write_manifest()  method.

.. code-block:: json

   "design": {
        "defvalue": null,
        "lock": "false",
        "require": null,
        "shorthelp": "Design top module name",
        "switch": "-design <str>",
        "type": "str",
        "value": "hello_world"
    },


To handle complex scenarios required by advanced PDKs, the Schema supports dynamic nested dictionaries. A 'default' keyword is used to define the dictionary structure during objection creation. Populating the object dictionary with actual keys is done by the user during compilation setup. The example below illustrates how 'default' is used as a placeholder for the library name and corner. These dynamic dictionaries makes it easy to set up an arbitrary number of libraries and corners in a PDK using Python loops.

.. code-block:: python

   lib = 'default
   corner = 'default'
   cfg['library'][lib]['nldm'] = {}
   cfg['library'][lib]['nldm'][corner] = {}
   cfg['library'][lib]['nldm'][corner]['default'] = {
       'switch': "-library_nldm 'lib corner format <file>'",
       'require': None,
       'type': '[file]',
       'lock': 'false',
       'copy': 'false',
       'defvalue': [],
       'filehash': [],
       'hashalgo': 'sha256',
       'date': [],
       'author': [],
       'signature': [],
       'shorthelp': 'Library NLDM timing model',
       'example': [
       "cli: -library_nldm 'lib ss lib ss.lib.gz'",
       "api: chip.set('library','lib','nldm','ss','lib','ss.lib.gz')"],
       'help': """
       Filepaths to NLDM models. Timing files are specified on a per lib,
       per corner, and per format basis. Legal file formats are lib (ascii)
       and ldb (binary). File decompression is handled automatically for
       gz, zip, and bz2 compression formats.
       """
    }

The SiliconCompiler Schema is roughly divided into the following major sub-groups:

.. list-table::
   :widths: 10 10 50
   :header-rows: 1

   * - Group
     - Parameters
     - Description

   * - *root*
     - 52
     - Source files and compilation options

   * - **eda**
     - 22
     - Individual tool settings

   * - **flowgraph**
     - 6
     - Execution flow definition

   * - **pdk**
     - 38
     - PDK related settings

   * - **asic**
     - 21
     - ASIC related settings

   * - **fpga**
     - 6
     - FPGA related settings

   * - **mcmm**
     - 8
     - Advanced timing analysis settings

   * - **library**
     - 46
     - Library/package definitions

   * - **metric**
     - 35
     - Metric tracking

   * - **record**
     - 39
     - Compilation history tracking

   * - **package**
     - 32
     - Packaging manifest

   * - **total**
     - 306
     -

Refer to the :ref:`Schema <SiliconCompiler Schema>` and :ref:`Python API<Core API>` sections of the reference manual for more information. Another good resource is the single file `Schema source code <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/schema.py>`_.
