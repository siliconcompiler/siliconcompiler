.. _glossary:

Glossary
===================================

The following set of terms represents fundamental SiliconCompiler definitions used throughout the documentation.

.. glossary::

    default
       Reserved SiliconCompiler schema key that can be replaced by any legal string.

    dictionary
       Associative array, ie. a collection of key-value pairs.

    edge
       A directed connection between a tail node and head nodes in a flowgraph.

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

    parameter
       Schema leaf cell with a set of pre-defined key/value pairs.

    project
       Instance of SiliconCompiler Project class used to compile a design.

    program
       User specified program with one (or more) project instances.

    schema
       Nested dictionary of parameters.

    step
       A discrete function in a flowgraph.

    task
       An atomic (step, index) task to be executed.

    tool
       Executable associated with a task in a flowgraph.
