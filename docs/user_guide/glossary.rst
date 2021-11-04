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

    flowgraph
      A directed acyclic graph specification of the hardware compilation.

    index
       A compilation step scenario operating on input data.

    job
       Execution of complete or partial compilation flowgraph.

    keypath
       Ordered list of keys used to access a schema parameter.

    keywords
       Reserved strings that cannot be used as key names.

    list
       An ordered and mutable sequence of elements.

    manifest
       JSON file representation of the SiliconCompiler schema.

    parameter
       Schema leaf cell with a set of pre-defined key/value pairs.

    program
       User specified program with one (or more) chip instances, steps, jobs, indices.

    schema
       Nested dictionary of parameters.

    step
       An discrete function in a flowgraph.

    task
       An atomic (step, index) action to be executed in a flowgraph.

    tool
       Executable associated with a task in a flowgraph.
