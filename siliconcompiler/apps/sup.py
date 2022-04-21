import argparse
import sys
import re
import siliconcompiler as sc
from siliconcompiler.package import Sup

def main():

    progname = "sup"
    usage = f"""{progname} <command> [options]
    """
    description = "SiliconCompiler package manager"
    epilog = f"""
------------------------------------------------------------
The Silicon Unified Packager ('sup') is the SiliconCompiler
package management utility for installing, upgrading,
configuring, and removing design packages from a local
computer.

SUP packages are...

* JSON files directly produced by SiliconCompiler
* named <design>.<semver>.sup.gz
* included in a project with the 'package,dependency' schema
* resolved with the update() core method
* installed in ~/.sc/registry by default
* organized as follows:
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

Supported Commands:

check     : Check package
publish   : Publish package
install   : Install package
uninstall : Uninstall package
show      : Show package information
list      : List packages in local install cache
index     : List packages in registry

See https://docs.siliconcompiler.com for more information

------------------------------------------------------------
"""

    parser = argparse.ArgumentParser(
        prog=progname,
        usage=usage,
        epilog=epilog,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Function to execute
    parser.add_argument('command',help="command to run")

    # Package Name
    parser.add_argument('name',
                        nargs='*',
                        help="package name")

    # Options
    parser.add_argument("-v", "--version",
                        action="store_true",
                        help="show version and ext")

    parser.add_argument("-registry",
                        metavar='',
                        action='append',
                        help="registry list")

    parser.add_argument("-loglevel",
                        metavar='',
                        help="logging level")

    parser.add_argument("-nodeps",
                        action="store_true",
                        help="don't include dependencies")

    # Create command line
    args = parser.parse_args()

    # Reading values
    command = args.command
    packlist = args.name
    registry = args.registry

    package_commands = ('check', 'publish', 'show', 'install', 'uninstall')
    global_commands = ('clear', 'list', 'index')

    if command in package_commands:
        for item in packlist:
            p = sc.package.Sup()
            p.chip.set('design', item)
            if command == 'check':
                p.check(item)
            elif command == 'publish':
                p.publish(item, registry)
            elif command == 'install':
                p.install(item, registry=registry)
            elif command == 'uninstall':
                p.uninstall()
            elif command == 'show':
                p.show()
    else:
        p = sc.package.Sup()
        if command == 'clear':
            p.clear()
        elif command == 'list':
            p.getlist()
        elif command == 'index':
            p.index()


#########################
if __name__ == "__main__":
    sys.exit(main())
