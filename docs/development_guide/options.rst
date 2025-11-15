.. _user_settings:

User Settings
=============

SiliconCompiler provides a robust system for managing persistent user configuration across different sessions and tools.
This system allows you to define default behaviors—such as your preferred scheduler, remote processing credentials, or compilation flags—once, and have them automatically applied to every new :class:`.Project`.

The settings are managed by a centralized :class:`.SettingsManager` which ensures thread-safe and process-safe access to the configuration file using file locking.
This is particularly important in environments where multiple SiliconCompiler processes (e.g., parallel build steps) might attempt to read or write settings simultaneously.

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

Workflow
--------

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
