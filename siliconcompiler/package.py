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

    def __init__(self):

        self.chip = siliconcompiler.Chip()
        self.registry = 'https://'

        if 'SC_CACHE' in os.environ:
            self.cache = os.environ['SC_CACHE']
        else:
            self.cache = os.path.join(os.environ['HOME'],'.sc','registry')

    ############################################################################
    def check(self, filename):
        '''
        Checks that manifest is ready to publish.

        Args:
            filename (filepath): Path to a manifest file to be loaded

        '''

        self.chip.read_manifest(filename, clobber=True)
        self.chip.check_manifest()

        #TODO: Add packaging specific checks
        for keylist in self.chip.getkeys():
            if (keylist[0] in ('package') and
                keylist[1] in ('version', 'description', 'license')):
                if self.chip.get(*keylist) in ("null", None, []):
                    self.chip.error = 1
                    self.chip.logger.error(f"Package missing {keylist} information")

        # Exit on errors
        if self.chip.error > 0:
            self.chip.logger.info(f"Exiting due to previous errors during")
            sys.exit()

        return(0)

    ############################################################################
    def publish(self, filename, registry=None,
                history=True, metrics=True, imports=True, exports=True):
        '''
        Publish a chip manifest to the registry.

        Args:
            filename (filepath): Path to a manifest file to be loaded
            registry (str): File system directory or IP address of registry
            history (bool): Include job history in package
            metrics (bool): Include metrics in package
            imports (bool): Include import files (sourcs) in package
            exports (bool): Include export files (outputs) in package

        '''

        if registy is None:
            registry = self.registry
        elif len(registry)==1:
            registry = registry
        else:
            registry = registry[0]

        # Call check first
        self.check(filename)

        # extract basic information
        design = self.chip.get('design')
        version = self.chip.get('package', 'version')
        ifile = f"{design}-{version}.sup.gz"

        #TODO: prune based on packaging options
        self.chip.write_manifest(f"{design}-{version}.sup.gz")

        if re.match(r'http', registry):
            #TODO
            pass
        else:
            odir = os.path.join(registry, design, version)
            os.makedirs(odir, exist_ok=True)
            ofile = os.path.join(odir,f"{design}-{version}.sup.gz")
            shutil.copyfile(ifile, ofile)

        return(0)

    ############################################################################
    def install(self, name, registry=None, nodeps=False):
        '''
        Install a registry package in the local cache.

        Args:
            name (str): Package to install in formatl <design>-(<semver>)?
            registry (str): List of registries tos search
            nodeps (bool): Don't install dependency tree if True
        '''

        auto = True

        if registry is None:
            reglist = self.registry
        else:
            reglist = registry

        # Load the first package
        local = self.chip._build_index(self.cache)
        remote = self.chip._build_index(reglist)

        # Allo name to be with or without version
        m =re.match(r'(.*?)-([\d\.]+)$',name)
        if m:
            design = m.group(1)
            version = m.group(2)
        else:
            design = name
            #TODO: fix to take the latest ver
            version = remote[design]['ver']

        deps = {}
        deps[design] = version

        #TODO: allow for installing one package only (nodeps)
        depgraph = self.chip._find_deps(self.cache, local, remote, design, deps, True)


        return(0)

    ############################################################################
    def uninstall(self, name, version=None):
        '''
        Remove a package from the local cache.
        '''

        packagedir = os.path.join(self.cachedir, design, version)
        rmfile = os.path.join(packagedir,f"{design}-{version}.sup.gz")

        #TODO:

        os.remove(rmfile)

        return(0)

    ############################################################################
    def show(self, name):
        '''
        Shows information about a cached package.
        '''

        local_index = self._build_index(self.cachedir)

        print(local_index)

        return(0)


    ############################################################################
    def clear(self):
        '''
        Removes all packages from the local cache.
        '''

        packagedir = os.path.join(self.cachedir, design, version)
        rmfile = os.path.join(packagedir,f"{design}-{version}.sup.gz")

        os.remove(rmfile)

        return(0)

    ############################################################################
    def getlist(self):
        '''
        List installed packages.
        '''

        if name is None:
            name = self.chip.get('design')

        if alldeps:
            print("fetch all deps")
        else:
            print("fetch one package only")

        return(0)



    ############################################################################
    def getindex(self):
        '''
        List installed packages.
        '''

        if name is None:
            name = self.chip.get('design')

        if alldeps:
            print("fetch all deps")
        else:
            print("fetch one package only")

        return(0)

    ############################################################################
    def getinfo(self):
        '''
        List installed packages.
        '''

        if name is None:
            name = self.chip.get('design')

        if alldeps:
            print("fetch all deps")
        else:
            print("fetch one package only")

        return(0)
