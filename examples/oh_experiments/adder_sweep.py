#!/usr/bin/env python3

from siliconcompiler import ASICProject, DesignSchema
from siliconcompiler.targets import freepdk45_demo

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def main():
    # datawidths to check
    datawidths = [8, 16, 32, 64]

    # Setup design
    design = DesignSchema("oh_add")
    design.set_dataroot("oh",
                        "git+https://github.com/aolofsson/oh",
                        "23b26c4a938d4885a2a340967ae9f63c3c7a3527")
    for n in datawidths:
        with design.active_dataroot("oh"), design.active_fileset(f"rtl.{n}"):
            design.set_topmodule("oh_add")
            design.add_file("mathlib/hdl/oh_add.v")
            design.set_param("N", str(n))

    proj = ASICProject(design)
    proj.load_target(freepdk45_demo.setup)
    proj.set_flow("synflow")

    # Gather Data
    area = []
    for n in datawidths:
        proj.add_fileset(f"rtl.{n}", clobber=True)
        proj.set("option", "jobname", f"N{n}")
        proj.run()

        area.append(proj.history(f"N{n}").get('metric', 'cellarea', step='synthesis', index='0'))

    if plt:
        # Plot Data
        plt.subplots(1, 1)
        plt.plot(datawidths, area)
        plt.show()
    else:
        proj.logger.info(f'areas: {area}')
        proj.logger.warning('Install matplotlib to automatically plot this data!')
        return area


if __name__ == '__main__':
    main()
