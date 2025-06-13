Schema API
----------

This chapter describes all public methods in the SiliconCompiler Schema Python API.
Refer to the User Guide for architecture concepts and the :ref:`glossary` for terminology and keyword definitions.

Useful APIs
===========

.. currentmodule:: siliconcompiler.schema

**Base schema:**

.. autosummary::
    :nosignatures:

    BaseSchema.set
    BaseSchema.add
    BaseSchema.get
    BaseSchema.getkeys
    BaseSchema.getdict
    BaseSchema.valid
    BaseSchema.unset
    BaseSchema.remove
    BaseSchema.write_manifest
    BaseSchema.read_manifest
    BaseSchema.from_manifest

**Editing schema:**

.. autosummary::
    :nosignatures:

    EditableSchema.insert
    EditableSchema.remove
    EditableSchema.search

Metrics Classes
===============

.. autoclass:: siliconcompiler.DesignSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.RecordSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.MetricSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.PDKSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.FlowgraphSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.ChecklistSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.ToolSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.ASICSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.FPGASchema
    :members:
    :show-inheritance:
    :inherited-members:

Full API
========

.. autoclass:: BaseSchema
    :members:
    :private-members: +_from_dict,_parent

.. autoclass:: EditableSchema
    :members:

.. autoclass:: SafeSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: CommandLineSchema
    :members:

.. autoclass:: Journal
    :members:

.. autoclass:: NamedSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.dependencyschema.DependencySchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: PackageSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: Parameter
    :members:

.. autoclass:: siliconcompiler.schema.parametervalue.NodeListValue
    :members:

.. autoclass:: siliconcompiler.schema.parametervalue.NodeValue
    :members:

.. autoclass:: siliconcompiler.schema.parametervalue.PathNodeValue
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.schema.parametervalue.DirectoryNodeValue
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.schema.parametervalue.FileNodeValue
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.schema.parametertype.NodeType
    :members:

.. autoclass:: siliconcompiler.schema.parametertype.NodeEnumType
    :members:

.. autoclass:: siliconcompiler.schema.parameter.Scope
    :members:
    :undoc-members:

.. autoclass:: siliconcompiler.schema.parameter.PerNode
    :members:
    :undoc-members:

.. autoclass:: siliconcompiler.flowgraph.FlowgraphNodeSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.flowgraph.RuntimeFlowgraph
    :members:

.. autoclass:: siliconcompiler.tool.TaskSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.tool.TaskError
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.tool.TaskTimeout
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.tool.TaskExecutableNotFound
    :members:
    :show-inheritance:
    :inherited-members:
