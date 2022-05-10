# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import os
import sys

#Shorten siliconcompiler as sc
import siliconcompiler
import siliconcompiler.client

###########################
def main():


    progname = "sc"
    description = """
    ------------------------------------------------------------
    SiliconCompiler is an open source compiler framework that
    aims to enable automated translation from source code to
    silicon.

    The sc program includes the followins steps.

    1. Read command line arguments
    2. If not set, 'design' is set to base of first source file.
    3. If not set, 'target' is set to 'asicflow_freepdk45.
    4. Run compilation
    5. Display summary

    Sources: https://github.com/siliconcompiler/siliconcompiler
    ------------------------------------------------------------
    """

    # find design name for object init
    design = 'none'
    for i , item in enumerate(sys.argv):
        if item == "-design":
            design = sys.argv[i+1]

    # Create a base chip class.
    chip = siliconcompiler.Chip(design)

    # Read command-line inputs and generate Chip objects to run the flow on.
    chip.create_cmdline(progname,
                        description=description)

    # Set design if none specified
    if not chip.get('design'):
        sources = chip.get('source')
        if len(sources) > 0:
            topfile = chip.get('source')[0]
        else:
            chip.logger.error('Invalid arguments: either specify -design or provide sources.')
            sys.exit(1)

        topmodule = os.path.splitext(os.path.basename(topfile))[0]
        chip.set('design', topmodule)

    # Set demo target if none specified
    if not chip.get('option', 'target'):
        chip.load_target("freepdk45_demo")

    # Storing user entered steplist/args before running
    if chip.get('arg','step'):
        steplist = [chip.get('arg','step')]
    else:
        steplist = chip.get('option', 'steplist')

    # Run flow
    chip.run()

    # Print Job Summary
    chip.summary(steplist=steplist)

#########################
if __name__ == "__main__":

    sys.exit(main())
