import os
import shutil
import siliconcompiler

class Sup:
    '''SiliconCompiler Unified Package (SUP) class.

    This is the main object used to interact with the SiliconCompiler
    Unified Packager API.

     Args:
       filename: Manifest to package.

    '''

    def __init__(self):

        self.chip = siliconcompiler.Chip()

        if 'SC_CACHE' in os.environ:
            self.cachedir = os.environ['SC_CACHE']
        else:
            self.cachedir = os.path.join(os.environ['HOME'],'.sc','registry')

    ############################################################################
    def package(self, filename,
                jobs=None, metrics=False, imports=False, exports=False):
        '''
        Create a SUP package based on current chip object.

        The package is placed in the local cache $SC_HOME/registry. SC_HOME is
        an environment variable that is set to $HOME/.sc by default.

        Directory structure in $SC_HOME/registry.

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

        '''

        # read in json object
        self.chip.read_manifest(filename, clobber=True)

        # creating internal cache structure
        design = self.chip.get('design')
        version = self.chip.get('package', 'version')
        packagedir = os.path.join(self.cachedir, design, version)
        os.makedirs(packagedir, exist_ok=True)

        # TODO: prune based on packaging options
        self.chip.write_manifest(os.path.join(packagedir,f"{design}-{version}.sup.gz"))

        return(0)

    ############################################################################
    def publish(self, registry=None):
        '''
        Publish package to a registry.
        '''

        design = self.chip.get('design')
        version = self.chip.get('package', 'version')
        packagedir = os.path.join(self.cachedir, design, version)
        ifile = os.path.join(packagedir,f"{design}-{version}.sup.gz")

        if registry:
            regdir=os.path.join(registry, design, version)
            ofile = os.path.join(regdir,f"{design}-{version}.sup.gz")
            os.makedirs(regdir, exist_ok=True)
            shutil.copyfile(ifile, ofile)

        return(0)

    ############################################################################
    def install(self, design, registry=None, version=None, alldeps=True):
        '''
        Install a package in the local cache.
        '''

        # Local management
        if registry:
            regdir=os.path.join(registry, design, version)
            ifile = os.path.join(regdir,f"{design}-{version}.sup.gz")

        ofile = os.path.join(cachedir,f"{design}-{version}.sup")

        os.makedirs(regdir, exist_ok=True)
        shutil.copyfile(ifile, ofile)

        if name is None:
            name = self.chip.get('design')

        if alldeps:
            print("fetch all deps")
        else:
            print("fetch one package only")

        return(0)

    ############################################################################
    def remove(self, design, version, alldeps=True):
        '''
        Remove a package from the local cache.
        '''

        packagedir = os.path.join(self.cachedir, design, version)
        rmfile = os.path.join(packagedir,f"{design}-{version}.sup.gz")

        #TODO:

        os.remove(rmfile)

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
    def list(self):
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
    def build(self, name=None, job=None, alldeps=True, clean=True):
        '''
        Build the named package and its dependencies.

        - All intermediate files are cleaned up by default.
        - The order of the build is done bottom up.
        - Assumes that it's actually possible
        - Ideally the 'binaries' would be shipped with the package.

        '''

        if name is None:
            name = self.chip.get('design')

        if alldeps:
            print("build dep")
        else:
            print("build ")

        return(0)
