# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.
import sys

from siliconcompiler import Project


###########################
def main():
    progname = "summarize"
    description = """
    ------------------------------------------------------------
    Utility script to print job summary from a manifest
    ------------------------------------------------------------
    """
    # Read command-line inputs and generate project objects to run the flow on.
    proj = Project.create_cmdline(
        progname,
        description=description,
        switchlist=['-jobname'],
        use_cfg=True, use_sources=False)

    if not proj.get('option', 'design'):
        return 1

    # Print Job Summary
    proj.summary()

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
