Glossary
===================================

The following set of terms represents fundamental SiliconCompiler definitions used throughout the documentation.

.. glossary::

    chip
       Instance of SiliconCompiler Chip() class used to compile a design.

    default
       Reserved SiliconCompiler schema key that can be replaced by any legal string.

    dictionary
       Associative array, ie. a collection of key-value pairs.

    edge
       A directed connection between a tail node and head nodes in a flowgraph

    flowgraph
       A directed acyclic graph specification of the hardware compilation.

    index
       A compilation step scenario operating on input data.

    job
       Execution of complete or partial compilation flowgraph.

    keys
       Immutable strings used as index into dictionary.

    keypath
       Ordered list of keys used to access schema parameters.

    keywords
       Reserved strings that cannot be used as key names.

    list
       An ordered and mutable sequence of elements.

    manifest
       JSON file representation of the SiliconCompiler schema.

    node
       An task in the flowgraph.

    parameter
       Schema leaf cell with a set of pre-defined key/value pairs.

    program
       User specified program with one (or more) chip instances.

    schema
       Nested dictionary of parameters.

    step
       An discrete function in a flowgraph.

    task
       An atomic (step, index) combination to be executed.

    tool
       Executable associated with a task in a flowgraph.
