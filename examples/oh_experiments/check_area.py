#!/usr/bin/env python3

# Import necessary classes from the siliconcompiler library.
from siliconcompiler import ASICProject, Design
# Import a pre-defined target, which sets up the PDK, libraries, and toolchain.
from siliconcompiler.targets import freepdk45_demo

# Import standard Python libraries for file system operations and system interaction.
import glob
import sys
import os.path

# Import type hinting for better code clarity.
from typing import Callable, List


def checkarea(design: Design, filesets: List[str], target: Callable[[ASICProject], None]):
    '''Runs synthesis for a list of designs and reports the area.

    This function iterates through a provided list of filesets (each representing
    a unique module), runs a synthesis flow for each one, and prints the
    resulting cell count and area in CSV format.

    Args:
        design (Design): The master design object containing all filesets.
        filesets (List[str]): A list of fileset names to process.
        target (Callable[[ASICProject], None]): A SiliconCompiler target setup function, such as
            freepdk45_demo.
    '''

    # Print a header for the CSV output.
    print("module,cells,area")

    # Loop through each fileset (i.e., each module) provided.
    for fileset in filesets:
        # Create a new, clean ASICProject for each module. This is important
        # to ensure that the settings from one run do not affect the next.
        proj = ASICProject(design)
        # Add the specific fileset for the current module to the project.
        proj.add_fileset(fileset)

        # Load the target configuration (PDK, libs, tools).
        target(proj)

        # Set a unique jobname for this run based on the fileset name. This helps
        # organize the output directories (e.g., build/oh_add/).
        proj.set("option", "jobname", fileset)
        # Specify the 'synflow', a pre-defined flow for running synthesis.
        proj.set_flow("synflow")

        # Execute the synthesis flow.
        proj.run()

        # After the run, retrieve metrics from the results history.
        # We specify the jobname to ensure we get data from the correct run.
        cells = proj.history(fileset).get('metric', 'cells', step='synthesis', index='0')
        area = proj.history(fileset).get('metric', 'cellarea', step='synthesis', index='0')

        # Extract the module name from the fileset name (e.g., "rtl.oh_add" -> "oh_add").
        module_name = fileset.split('.')[-1]
        # Print the results for this module in CSV format.
        proj.logger.info(f"{module_name},{cells},{area}")


def main(limit: int = -1):
    '''
    Scans a library of Verilog files, creates a SiliconCompiler design
    object with a fileset for each module, and then runs the checkarea
    function to characterize them.

    Args:
        limit (int): The maximum number of modules to process. Defaults to -1,
            which means all modules will be processed. Useful for quick tests.
    '''
    # --- Design Setup ---
    # Create a master Design to hold all our module configurations.
    design = Design("oh")
    # Set up a 'dataroot' to fetch the design sources from a GitHub repository.
    # SiliconCompiler clones the repo and uses the specific commit for reproducibility.
    design.set_dataroot("oh",
                        "git+https://github.com/aolofsson/oh",
                        "23b26c4a938d4885a2a340967ae9f63c3c7a3527")

    # Get the local path to the cloned dataroot.
    oh_path = design.get_dataroot("oh")
    # Use glob to find all Verilog files in the target directory.
    verilog_files = glob.glob(os.path.join(oh_path, "asiclib", "hdl", "*.v"))

    # Iterate through each discovered Verilog file.
    for file in verilog_files:
        # --- File Filtering ---
        # Create a blocklist of files that are not synthesizable modules
        # (e.g., infrastructure, simulation models, empty wrappers).
        if os.path.basename(file) in [
                'asic_keeper.v',
                'asic_antenna.v',
                'asic_header.v',
                'asic_footer.v',
                'asic_decap.v']:
            # Skip the current file and move to the next one.
            continue

        # --- Fileset Creation ---
        # Infer the top-level module name from the filename (e.g., "oh_add.v" -> "oh_add").
        top_module = os.path.basename(file).split(".")[0]

        # Create a unique fileset for this module (e.g., "rtl.oh_add").
        with design.active_dataroot("oh"), design.active_fileset(f"rtl.{top_module}"):
            # Set the top module for this specific fileset.
            design.set_topmodule(top_module)
            # Add the Verilog source file. The path is relative to the dataroot.
            design.add_file(os.path.join("asiclib", "hdl", os.path.basename(file)))

    # --- Execution ---
    # Get a sorted list of all the "rtl.*" filesets we just created.
    # The slice [0:limit] applies the user-defined limit on how many to process.
    filesets = sorted([key for key in design.getkeys("fileset") if key.startswith('rtl')])[0:limit]

    # Call the main processing function with the fully configured design object.
    checkarea(design, filesets, freepdk45_demo)

    return 0


#########################
# Main execution block
#########################
if __name__ == "__main__":
    # This makes the script runnable from the command line.
    # It calls the main function and exits with its return code.
    sys.exit(main())
