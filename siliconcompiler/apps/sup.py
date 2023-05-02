import argparse
import sys
import siliconcompiler as sc


def main():

    progname = "sup"
    usage = f"""{progname} <command> [options]
    """
    description = "SiliconCompiler package manager"
    epilog = """
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
info      : Show package information
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
    parser.add_argument('command', help="command to run")

    # Package Name
    parser.add_argument('name',
                        nargs='*',
                        help="package name(s)")

    # Options
    parser.add_argument("-v", "--version",
                        action="store_true",
                        help="show version and ext")

    parser.add_argument("-r", "--registry",
                        metavar='',
                        action='append',
                        help="registry list")

    parser.add_argument("-l", "--loglevel",
                        metavar='',
                        help="logging level")

    parser.add_argument("--nodeps",
                        action="store_true",
                        help="don't include dependencies")

    # Create command line
    args = parser.parse_args()

    # Reading values
    command = args.command
    packlist = args.name
    registry = args.registry

    if packlist == []:
        packlist is None

    if command in ('clear'):
        p = sc.package.Sup(registry)
        p.clear()
    else:
        for item in packlist:
            p = sc.package.Sup(registry)
            p.chip.set('design', item)
            if command == 'check':
                p.check(item)
            elif command == 'publish':
                p.publish(item, registry[0])
            elif command == 'install':
                p.install(item)
            elif command == 'uninstall':
                p.uninstall(item)
            elif command == 'search':
                p.search(item)
            elif command == 'info':
                p.info(item)


#########################
if __name__ == "__main__":
    sys.exit(main())
