Package Management
==================

The SiliconCompiler project has built in support for package management thanks to the schema
architecture and automated generation of chip manifests at every tasks. The package management
system for SC is called the "Silicon Unified Packager" (SUP).

SUP comliant packages are...

* JSON files produced by the SiliconCompiler schema and core API
* named <design>.<semver>.sup.gz
* included in a project through the 'package, dependency' schema parameter
* resolved within a design through the update() core method
* installed in the local ~/.sc/registry cache by default
* organised according to the following directory structure
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

Package management can be done directly through the 'sup' command line app which includes
the following operations:

check     : Check package for legality before publishing
publish   : Publish a package to the registry
install   : Install a package from the registry
uninstall : Uninstall a package
show      : Show package information
list      : List packages in local install cache
index     : List packages in registry

Package management can also be handled automatically from within a compilatio program by using
the core update() method.

The following schema parameters are used for package management:

* depgraph: Resolved package dependency list (automatically updated by SC)
* registry: List of registry filepaths and IP address.
* autoinstall: Enables autoinstall by the core update() method
* package, dependency: list of package dependencies for the current design
