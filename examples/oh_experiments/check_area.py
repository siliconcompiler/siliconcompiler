#!/usr/bin/env python3

from siliconcompiler import ASICProject, DesignSchema
from siliconcompiler.targets import freepdk45_demo

import glob
import sys

import os.path


def checkarea(design, filesets, target):
    '''
    Runs SC through synthesis and prints out the module name, cell count,
    and area as a csv format ready to be imported into a spreadsheet
    program.

    Args:
    filelist (list): List of files to process. Naming should be "module".v.
    libdir (str): Path to required Verilog sources.
    target (module): Name of the SC target. For example, freepdk45_demo.
    '''

    for fileset in filesets:
        proj = ASICProject(design)
        proj.add_fileset(fileset)

        proj.load_target(target)

        proj.set("option", "jobname", fileset)
        proj.set_flow("synflow")

        proj.run()
        cells = proj.history(fileset).get('metric', 'cells', step='synthesis', index='0')
        area = proj.history(fileset).get('metric', 'cellarea', step='synthesis', index='0')
        proj.logger.info(f"{fileset},{cells},{area}")

    return 0


def main(limit=-1):
    # Setup design
    design = DesignSchema("oh")
    design.set_dataroot("oh",
                        "git+https://github.com/aolofsson/oh",
                        "23b26c4a938d4885a2a340967ae9f63c3c7a3527")
    oh_path = design.get_dataroot("oh")
    for file in glob.glob(os.path.join(oh_path, "asiclib", "hdl", "*.v")):
        if os.path.basename(file) in [
                'asic_keeper.v',
                'asic_antenna.v',
                'asic_header.v',
                'asic_footer.v',
                'asic_decap.v']:
            continue

        top = os.path.basename(file).split(".")[0]
        with design.active_dataroot("oh"), design.active_fileset(f"rtl.{top}"):
            design.set_topmodule(top)
            design.add_file(os.path.join("asiclib", "hdl", os.path.basename(file)))

    filesets = sorted(design.getkeys("fileset"))[0:limit]
    return checkarea(design, filesets, freepdk45_demo.setup)


#########################
if __name__ == "__main__":
    sys.exit(main())
