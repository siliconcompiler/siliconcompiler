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

Schema Classes
==============

.. autoclass:: siliconcompiler.Design
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.library.LibrarySchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.schema_support.record.RecordSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.schema_support.metric.MetricSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.PDK
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.Flowgraph
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.Checklist
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.TaskSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.FPGA
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.StdCellLibrary
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.Schematic
    :members:
    :show-inheritance:
    :inherited-members:


ASIC Constraint Classes
=======================

.. autoclass:: siliconcompiler.constraints.ASICTimingConstraintSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.ASICTimingScenarioSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.ASICAreaConstraint
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.ASICPinConstraints
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.ASICPinConstraint
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.ASICComponentConstraints
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.ASICComponentConstraint
    :members:
    :show-inheritance:
    :inherited-members:

FPGA Constraint Classes
=======================

.. autoclass:: siliconcompiler.constraints.FPGATimingConstraintSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.FPGATimingScenarioSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.FPGAComponentConstraints
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.constraints.FPGAPinConstraints
    :members:
    :show-inheritance:
    :inherited-members:

Core Schema Classes
===================

.. autoclass:: BaseSchema
    :members:
    :private-members: +_from_dict,_parent

.. autoclass:: EditableSchema
    :members:

.. autoclass:: SafeSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: Journal
    :members:

.. autoclass:: NamedSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: Parameter
    :members:

.. autoclass:: siliconcompiler.schema.parametervalue.NodeListValue
    :members:

.. autoclass:: siliconcompiler.schema.parametervalue.NodeSetValue
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

Supporting Classes
==================

.. autoclass:: siliconcompiler.schema_support.dependencyschema.DependencySchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.schema_support.cmdlineschema.CommandLineSchema
    :members:

.. autoclass:: siliconcompiler.schema_support.pathschema.PathSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.schema_support.filesetschema.FileSetSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.flowgraph.FlowgraphNodeSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.flowgraph.RuntimeFlowgraph
    :members:

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

.. autoclass:: siliconcompiler.schema_support.packageschema.PackageSchema
    :members:
    :show-inheritance:
    :inherited-members:

Inheritance
===========

.. scclassinherit::
    :classes: siliconcompiler/ASICProject,siliconcompiler/FPGAProject,siliconcompiler/LintProject,siliconcompiler/SimProject

.. scclassinherit::
    :classes: siliconcompiler/Design,siliconcompiler/PDK,siliconcompiler/FPGA,siliconcompiler/StdCellLibrary,siliconcompiler/Flowgraph,siliconcompiler/Checklist,siliconcompiler/TaskSchema
