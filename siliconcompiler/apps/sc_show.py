# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys

import os.path

from siliconcompiler import Project
from siliconcompiler.apps._common import pick_manifest


def main():
    progname = "sc-show"
    description = """
    --------------------------------------------------------------
    Restricted SC app that displays the layout of a design
    based on a file provided or tries to display the final
    layout based on loading the json manifest from:
    build/<design>/job0/<design>.pkg.json

    Examples:

    sc-show
    (displays build/adder/job0/write.gds/0/outputs/adder.gds)

    sc-show -design adder
    (displays build/adder/job0/write.gds/0/outputs/adder.gds)

    sc-show -design adder -arg_step floorplan
    (displays build/adder/job0/floorplan/0/outputs/adder.def)

    sc-show -design adder -arg_step place -arg_index 1
    (displays build/adder/job0/place/1/outputs/adder.def)

    sc-show -design adder -jobname rtl2gds
    (displays build/adder/rtl2gds/write.gds/0/outputs/adder.gds)

    sc-show build/adder/rtl2gds/adder.pkg.json
    (displays build/adder/rtl2gds/write.gds/0/outputs/adder.gds)

    sc-show -design adder -ext odb
    (displays build/adder/job0/write.views/0/outputs/adder.odb)

    sc-show build/adder/job0/route/1/outputs/adder.def
    (displays build/adder/job0/route/1/outputs/adder.def)
    """

    class ShowProject(Project):
        def __init__(self):
            super().__init__()

            self._add_commandline_argument(
                "cfg", "file", "configuration manifest")
            self._add_commandline_argument(
                "extension", "str", "Specify the extension of the file to show.",
                "-ext <str>")
            self._add_commandline_argument(
                "screenshot", "bool", "Generate a screenshot and exit.")

    show = ShowProject.create_cmdline(
        progname,
        description=description,
        switchlist=[
            '-design',
            '-arg_step',
            '-arg_index',
            '-jobname',
            '-cfg',
            '-ext',
            '-screenshot'])

    manifest = None
    filename = None
    if show.get("cmdarg", "input"):
        for file in show.get("cmdarg", "input"):
            if not manifest and file.lower().endswith(".pkg.json"):
                manifest = file
            elif not filename:
                filename = file

    # Attempt to load a manifest
    if not manifest:
        manifest = pick_manifest(show, src_file=filename)

    if not manifest:
        show.logger.error("Unable to find manifest")
        return 1

    show.logger.info(f'Loading manifest: {manifest}')
    project = Project.from_manifest(filepath=manifest)

    # Read in file
    if filename:
        project.logger.info(f"Displaying {filename}")

    if not project.find_files('option', 'builddir', missing_ok=True):
        project.logger.warning("Unable to access original build directory "
                               f"\"{project.get('option', 'builddir')}\", using \"build\" instead")
        project.set('option', 'builddir', 'build')

    success = project.show(filename,
                           extension=show.get("cmdarg", "extension"),
                           screenshot=show.get("cmdarg", "screenshot"))

    if os.path.isfile(success) and show.get("cmdarg", "screenshot"):
        project.logger.info(f'Screenshot file: {success}')

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
