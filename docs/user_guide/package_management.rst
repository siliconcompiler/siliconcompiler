Package Management
==================

.. warning::
   The features described on this page are work in progress, and may not be
   fully working yet.

Packages are automatically created by every SiliconCompiler task. Publishing and installing
these packages is further simplified through a set of built in package management methods
and a standalone SiliconCompiler Unified Package ('sup') command line utility.

Publishing a known good json object to a registry is simple::

  from siliconcompiler.package import Sup
  p = Sup()
  p.publish("daughter.pkg.json", registry)

Using packages from a a set of distributed registries is equally simple::

  chip = sc.Chip(design='mother')
  chip.set('package', 'dependency', 'daughter', '1.2.3')
  chip.set('option', 'registry', registry_list)
  chip.set('option', 'autoinstall', True)
  chip.update()
  chip.run()

Package management system features:

* JSON files produced by the SiliconCompiler schema and core API
* registries can be on disk folders or IP addresses compatible with the sup API.
* named <design>.<semver>.sup.gz
* included in a project through the :keypath:`package, dependency' schema parameter
* dependencies resolved within a design through the :meth:`.update()` core API method
* packages are installed in the local ~/.sc/registry cache by default
* registry packages organized according to the following directory structure

 .. code-block:: text

  <design>
         └── <version>
             ├── <jobname>
             │   ├── import (sources)
             │   └── export (results)
             ├── <jobname>
             │   ├── import
             │   └── export
             ├── <design>-<version>.html
             └── <design>-<version>.sup

Package management can be performed directly from Python or at the command line through
the :ref:`sup` app distributed with the SiliconCompiler package.

* check     : Check that manifest before publishing.
* publish   : Publish chip manifest to registry.
* install   : Install registry package in local cache.
* uninstall : Remove package from local cache.
* search    : Search for a package in registry.
* info      : Display package information.

Key schema parameters included for package management include:

* :keypath:`package, depgraph`: Resolved package dependency list (automatically updated by SC)
* :keypath:`option, registry`: List of registry filepaths and IP address.
* :keypath:`option, autoinstall`: Enables autoinstall by the core update() method
* :keypath:`package, dependency`: list of package dependencies for the current design
