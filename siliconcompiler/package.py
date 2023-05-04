import os
import sys
import re
import shutil
import siliconcompiler


class Sup:
    '''SiliconCompiler Unified Package (SUP) class.

    Main object used to interact with the SiliconCompiler
    Package Management System API.

    '''

    def __init__(self, design, registry=None):

        # TODO: when starting sup, do we know the
        self.chip = siliconcompiler.Chip(design)

        # Local cache location
        if 'SC_HOME' in os.environ:
            home = os.environ['SC_HOME']
        else:
            home = os.environ['HOME']

        self.cache = os.path.join(home, '.sc', 'registry')

        # List of remote registries
        if registry is None:
            self.registry = ['https://']
        elif isinstance(registry, list):
            self.registry = registry
        else:
            self.registry = [registry]

    ############################################################################
    def check(self, filename):
        '''
        Check that manifest before publishing.

        Args:
            filename (filepath): Path to a manifest file to be loaded

        '''

        self.chip.read_manifest(filename, clobber=True)
        check_ok = self.chip.check_manifest()

        # TODO: Add packaging specific checks
        for keylist in self.chip.allkeys():
            if (keylist[0] in ('package') and keylist[1] in ('version', 'description', 'license')):
                if self.chip.get(*keylist) in ("null", None, []):
                    self.chip.logger.error(f"Package missing {keylist} information.")
                    check_ok = False

        # Exit on errors
        if not check_ok:
            self.chip.logger.error("Exiting due to previous errors.")
            sys.exit()

        return 0

    ############################################################################
    def publish(self, filename, registry=None,
                history=True, metrics=True, imports=True, exports=True):
        '''
        Publish chip manifest to registry.

        Args:
            filename (filepath): Path to a manifest file to be loaded
            registry (str): File system directory or IP address of registry
            history (bool): Include job history in package
            metrics (bool): Include metrics in package
            imports (bool): Include import files (sources) in package
            exports (bool): Include export files (outputs) in package

        '''

        # First registry entry is the default
        if registry is None:
            registry = self.registry[0]
        elif isinstance(registry, list):
            registry = registry[0]

        # Call check first
        self.check(filename)

        # extract basic information
        version = self.chip.get('package', 'version')

        if re.match(r'http', registry):
            # TODO
            pass
        else:
            self.chip.logger.info(f"Publishing {self.chip.design}-{version} package to "
                                  f"registry '{registry}'")
            odir = os.path.join(registry, self.chip.design, version)
            os.makedirs(odir, exist_ok=True)
            ofile = os.path.join(odir, f"{self.chip.design}-{version}.sup.gz")
            self.chip.write_manifest(ofile)

        return 0

    ############################################################################
    def install(self, name, nodeps=False):
        '''
        Install registry package in local cache.

        Args:
            name (str): Package to install in format <design>-(<semver>)?
            registry (str): List of registries tos search
            nodeps (bool): Don't descend dependency tree if True
        '''

        # Load the first package
        local = self.chip._build_index(self.cache)
        remote = self.chip._build_index(self.registry)

        # Allow name to be with or without version
        m = re.match(r'(.*?)-([\d\.]+)$', name)
        if m:
            design = m.group(1)
            version = m.group(2)
        else:
            design = name
            # TODO: fix to take the latest ver
            version = list(remote[design].keys())[0]

        deps = {}
        deps[design] = [version]

        # TODO: allow for installing one package only (nodep tree)
        auto = True
        self.chip._find_deps(self.cache, local, remote, design, deps, auto)

        return 0

    ############################################################################
    def uninstall(self, name):
        '''
        Uninstall local package.

        If no version is specified, all versions of the design are removed.

        Args:
            name (str): Package to remove in format <design>-(<semver>)?

        '''

        # Allow name to be with or without version
        m = re.match(r'(.*?)-([\d\.]+)$', name)
        if m:
            design = m.group(1)
            ver = m.group(2)
        else:
            design = name
            ver = None

        if ver is None:
            shutil.rmtree(os.path.join(self.cache, design))
        else:
            shutil.rmtree(os.path.join(self.cache, design, ver))

        return 0

    ############################################################################
    def search(self, name=None):
        '''
        Search for a package in registry.

        Args:
            name (str): Package to searc in format <design>-(<semver>)?

        '''

        remote = self.chip._build_index(self.registry)

        m = re.match(r'(.*?)-([\d\.]+)$', name)
        if m:
            design = m.group(1)
            ver = m.group(2)
        else:
            design = name
            # TODO: handle multiple versions
            ver = None

        # TODO: handle multiple registries
        foundit = False
        for item in remote.keys():
            if item == design:
                for j in remote[item].keys():
                    reg = remote[item][j]
                    if ver is None:
                        foundit = True
                        self.chip.logger.info(f"Found package '{item}-{j}' in registry '{reg}'")
                    elif ver == j:
                        foundit = True
                        self.chip.logger.info(f"Found package '{item}-{j}' in registry '{reg}'")
                        break

        if not foundit:
            self.chip.logger.error(f"Package '{name}' is not in the registry.")
            sys.exit(1)
        else:
            supfile = os.path.join(remote[design][j], design, j, f"{design}-{j}.sup.gz")

        return supfile

    ############################################################################
    def info(self, name):
        '''
        Display package information.

        Args:
            name (str): Package to display in format <design>-(<semver>)?

        '''

        supfile = self.search(name)

        self.chip.read_manifest(supfile)

        for key in self.chip.allkeys():
            if key[0] == 'package':
                value = self.chip.get(*key)
                if value:
                    self.chip.logger.info(f"Package '{name}' {key[1]}: {value}")

    ############################################################################
    def clear(self):
        '''
        Removes all locally installed packages.
        '''

        all_packages = os.listdir(os.path.join(self.cache))
        for item in all_packages:
            os.removedirs(item)

        return 0
