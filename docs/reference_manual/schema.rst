.. _SiliconCompiler Schema:
.. _schema:

Schema
=====================

Keywords
---------

.. glossary::
   default
       Reserved SiliconCompiler schema key that can be replaced by any legal string.

Parameter Fields
-----------------

.. glossary::

    copy
        Whether to copy files into build directory, applies to files only

    enum
        List of strings containing the set of legal values for this parameter.

    example
        List of two strings, the first string containing an example for specifying the parameter using a command line switch, and a second string for setting the value using the core Python API. The examples can be pruned/filtered before the schema is dumped into a JSON file.

    hashalgo
        Hashing algorithm used to calculate filehash value.

    help
        Complete parameter help doc string. The help string serves as ground truth for describing the parameter functionality and should be used for long help descriptions in command line interface programs and for automated schema document generation. The long help can be pruned/filtered before the schema is dumped into a JSON file.

    lock
        Boolean value dictating whether the parameter can be modified by the set/get/add core API methods. A value of True specifiers that the parameter is locked and cannot be modified. Attempts to write to to a locked parameter shall result in an exception/error that blocks compilation progress.

    node
        Dictionary containing fields whose values may vary on a per-step/index basis. Sub-fields are described in :ref:`Per-node Parameter Fields`

    notes
        User entered 'notes'/'disclaimers' about value being set.

    pernode
        Enables/disables setting of value on a per node basis. Allowed values are 'never', 'option', or 'required'.

    require
        String that specifies scenarios, conditions, and modes for which the parameter must return a non-empty value. Valid requirement keywords include 'all' and 'fpga'/'asic'. The 'all' keyword specifies that the parameter must always have a non-empty value before running a flow. The 'fpga'/'asic' keyword specifies that that the parameter must have a non-empty value when the respective mode is being executed.  All Boolean values have a valid True/False default value and a requirement of 'all'.  The vast majority of schema parameters have requirements of None and empty values which can be overridden by the user based on need.

    scope
        Scope of parameter in schema

    switch
        String that specifies the equivalent switch to use in command line interfaces. The switch string must start with a '-' and cannot contain spaces.

    shorthelp
        Short help string to be used in cases where brevity matters. Use cases include JSON dictionary dumps and command line interface help functions.

    type
        The parameter type. Supported types include Python compatible types ('int', 'float', 'str', 'enum', and 'bool') and two custom file types ('file' and 'dir'). The 'file' and 'dir' type specify that the parameter is a 'regular' file or directory as described by Posix. All types can be specified as a Python compatible list type by enclosing the type value in brackets. (ie. [str] specifies that the parameter is a list of strings). Types can also be specified as tuples, using the Python-like parentheses syntax (eg. [(float,float)] specifies a list of 2-float tuples). Input arguments and return values of the set/get/add core methods are encoded as native Python types. When exporting the manifest to JSON, values are converted to the equivalent JSON type. Most types have a straightforward mapping, but note that values of "None" get mapped to "null", and both tuples and lists get mapped to arrays. Tuple-type parameters have their values normalized back into tuple form when a JSON manifest is read in.

    unit
        Implied unit for parameter value.


Per-node Parameter Fields
---------------------------

The following fields are specified inside the ``node`` dictionary on a per-step/index basis. Default values for each field are stored under the special keys ``"default", "default"``, and global values are specified under the special keys ``"global", "global"``.

.. glossary::
    author
        File author. The author string records the person/entity that authored/created each item in the list of files within 'value' parameter field. The 'author' field can be used to validate the provenance of the data used for compilation.

    date
        String containing the data stamp of each item in the list of files within 'value' parameter field. The 'date' field can be used to validate the provenance of the data used for compilation.

    filehash
        Calculated file hash value for each file in the 'value' field of the parameter.

    signature
        String recording a unique machine calculated string for each item in the list of files within 'value' parameter field. The 'signature' field can be used to validate the provenance of the data used for compilation.

    value
        Parameter value

Parameters
-----------------------------

.. schemagen::

Nested Schemas
----------------

The SC schema has two special top-level categories that store nested subsets of the schema rather than unique parameters.

history
++++++++

The "history" prefix stores configuration from past runs, indexed by jobname. Values are stored automatically at the end of :meth:`run()`, and only parameters tagged with the 'job' scope are stored. This can be used to go back and inspect the results of old runs. As a shortcut for accessing these stored values, most of the schema access functions support an optional ``job`` keyword arg. For example, the following line returns the number of errors from a synthesis step run as part of a job called "job0"::

    chip.get('metric', 'error', job='job0', step='syn', index='0')

library
++++++++

The "library" prefix stores the schema parameters of library chip objects that have been imported into the current chip object, keyed by library name. These values are accessed directly using the schema access functions. For example, the following line returns the path to a LEF file associated with a library called "mylib"::

    chip.find_files('library', 'mylib', 'output', stackup, 'lef')
