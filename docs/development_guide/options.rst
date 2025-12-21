.. _user_settings:

User Settings
=============

SiliconCompiler provides a robust system for managing persistent user configuration across different sessions and tools.
This system allows you to define default behaviors—such as your preferred scheduler, remote processing credentials, or compilation flags—once, and have them automatically applied to every new :class:`.Project`.

The settings are managed by a centralized :class:`.SettingsManager` which ensures thread-safe and process-safe access to the configuration file using file locking.
This is particularly important in environments where multiple SiliconCompiler processes (e.g., parallel build steps) might attempt to read or write settings simultaneously.
The user is not expected to directly interact with the :class:`.SettingsManager`, but instead should set and save the settings via the associated classes.

Storage Format
--------------

Settings are stored in a JSON file (typically located at ``~/.sc/settings.json``).
The file is organized into **categories**, allowing different tools and subsystems within SiliconCompiler to maintain their own isolated configuration spaces.

The JSON structure generally looks like this:

.. code-block:: json

    {
        "schema-options": {
            "scheduler,name": "slurm",
            "scheduler,queue": "hw_queue",
            "remote": true,
            "optmode": "2"
        },
        "other-category": {
            "setting_name": "value"
        }
    }

.. note::
   The settings manager uses a "last-write-wins" policy per key and protects file integrity with strict error handling.
   If the settings file becomes malformed, the manager will log an error and start with an empty configuration to prevent crashes.

Concurrency & Safety
--------------------

The underlying :class:`.SettingsManager` utilizes a file lock (``.lock``) alongside the JSON file. This ensures that:

1.  **Atomic Writes**: Partial writes are prevented.
2.  **Process Safety**: Multiple independent SiliconCompiler runs can safely read/write defaults without race conditions.
3.  **Error Recovery**: If the lock cannot be acquired within a timeout (default 1.0s), the operation logs an error and proceeds safely (e.g., by skipping the load or failing the save gracefully) to ensure your build pipeline doesn't hang indefinitely.

Schema Defaults (The 'schema-options' Category)
-----------------------------------------------

The most common use case for user settings is defining default values for the SiliconCompiler :class:`.OptionSchema`.
When a new :class:`.Project` is initialized, it automatically queries the settings manager for the ``schema-options`` category.

Key Mapping
~~~~~~~~~~~

Because the Schema is hierarchical (e.g., :keypath:`option,scheduler,name`), the keys in the JSON settings file are flattened using comma separation.

* Schema path: :keypath:`option,scheduler,name` :math:`\rightarrow` JSON key: ``"scheduler,name"``
* Schema path: :keypath:`option,remote` :math:`\rightarrow` JSON key: ``"remote"``

Workflow: Schema Defaults
^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Loading Defaults**:
   When you instantiate a project, SiliconCompiler automatically loads values from the settings file. These values act as the baseline defaults.

   .. code-block:: python

       # If settings.json contains "scheduler,name": "slurm"
       project = siliconcompiler.Project()

       # The project starts with slurm enabled
       print(project.option.scheduler.get_name())
       # Output: slurm

2. **Saving Defaults**:
   You can programmatically save your current configuration as the new user default using :meth:`.OptionSchema.write_defaults`.
   This method compares your current configuration against the built-in defaults and saves only the modified parameters to the ``schema-options`` category in the settings file.

   .. code-block:: python

       import siliconcompiler

       project = siliconcompiler.Project()

       # Configure your preferred environment
       project.option.scheduler.set_name("slurm")
       project.option.scheduler.set_queue("priority_queue")
       project.option.set_quiet(True)

       # Persist these settings to disk
       project.option.write_defaults()

       # Now, any future script you run will default to using Slurm on the 'priority_queue'
       # with quiet logging enabled.

Slurm Scheduler Settings (The 'scheduler-slurm' Category)
---------------------------------------------------------

In addition to the standard schema options, specific schedulers may require their own configuration settings.
For example, the Slurm scheduler uses the ``scheduler-slurm`` category to manage cluster-specific behaviors.

**Shared Paths**

One key setting for Slurm is ``sharedpaths``.
This defines a list of directory prefixes that are available on all nodes in the cluster (e.g., via NFS or GPFS).
When SiliconCompiler runs on a compute node, it checks if input files are located within these shared paths.
If they are, the files are used directly; otherwise, they are copied to the build directory to ensure accessibility.
This optimization significantly reduces network traffic and disk usage for large designs.

.. code-block:: json

    {
        "scheduler-slurm": {
            "sharedpaths": ["/nfs/tools", "/work/project"]
        }
    }

Workflow: Slurm Settings
^^^^^^^^^^^^^^^^^^^^^^^^

Unlike standard schema options, scheduler-specific settings (like ``sharedpaths``) are stored in their own category.
The :class:`.SlurmSchedulerNode` provides static helper methods to manage these configurations safely without needing to manually interact with the settings manager.

.. code-block:: python

    from siliconcompiler.scheduler.slurm import SlurmSchedulerNode

    # 1. Set the shared paths
    # These paths must be visible on all compute nodes.
    SlurmSchedulerNode._set_user_config("sharedpaths", ["/nfs/tools", "/work/project"])

    # 2. Persist changes to ~/.sc/settings.json
    SlurmSchedulerNode._write_user_config()

Show Task Preferences (The 'showtask' Category)
-----------------------------------------------

SiliconCompiler allows you to define preferred viewers for specific file extensions.
This is useful when multiple tools are capable of opening a specific file type (e.g., both KLayout and OpenROAD can view ``.def`` files) and you want to enforce a specific default.

This configuration is stored in the ``showtask`` category of your ``settings.json`` file. The key is the file extension (without the dot), and the value is the name of the tool (and optionally the task).

**Example Configuration**

.. code-block:: json

    {
        "showtask": {
            "gds": "klayout",
            "def": "openroad/show",
            "vcd": "gtkwave"
        }
    }

In this example:

* ``.gds`` files will always open with KLayout.
* ``.def`` files will always open with OpenROAD, specifically using the ``show`` task.
* ``.vcd`` files will always open with GTKWave.

If the preferred tool is not found or not registered, SiliconCompiler will fall back to its default discovery mechanism.
