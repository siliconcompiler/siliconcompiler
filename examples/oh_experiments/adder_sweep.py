#!/usr/bin/env python3

# Import necessary classes from the siliconcompiler library.
from siliconcompiler import ASICProject, DesignSchema
# Import a pre-defined target, which sets up the process technology (PDK),
# standard cell libraries, and toolchain.
from siliconcompiler.targets import freepdk45_demo

# Try to import matplotlib for plotting. If it's not installed, we'll
# fall back to printing the data to the console.
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def main():
    # Define the list of data widths we want to sweep through for our adder.
    datawidths = [8, 16, 32, 64]

    # --- Design Setup ---
    # A DesignSchema encapsulates all the source files, parameters, and
    # settings for a specific hardware design.
    design = DesignSchema("oh_add")

    # Set up a 'dataroot' to fetch the design's source files directly from a
    # GitHub repository. SiliconCompiler will clone this repo. We pin it to a
    # specific commit hash to ensure the results are reproducible.
    design.set_dataroot("oh",
                        "git+https://github.com/aolofsson/oh",
                        "23b26c4a938d4885a2a340967ae9f63c3c7a3527")

    # Loop through the specified data widths to create a unique 'fileset' for each one.
    # A fileset is a named collection of source files. This allows us to manage
    # different configurations of the same core design.
    for n in datawidths:
        # We use a 'with' context to set the active dataroot and fileset.
        # This creates filesets named "rtl.8", "rtl.16", etc.
        with design.active_dataroot("oh"), design.active_fileset(f"rtl.{n}"):
            # Define the top-level Verilog module for the design.
            design.set_topmodule("oh_add")
            # Add the Verilog source file to this fileset.
            design.add_file("mathlib/hdl/oh_add.v")
            # Set the Verilog parameter 'N' for this fileset. This is how we
            # pass the data width to the Verilog module. The synthesis tool
            # will use this value during elaboration.
            design.set_param("N", str(n))

    # --- Project Setup ---
    # An ASICProject links a design schema to a specific flow and target.
    proj = ASICProject(design)
    # Load the freepdk45_demo target, which configures the project for the
    # FreePDK45 technology and a demonstration tool setup.
    proj.load_target(freepdk45_demo.setup)
    # Set the flow to 'synflow', a pre-defined sequence of steps for running synthesis.
    proj.set_flow("synflow")

    # --- Data Gathering ---
    # This list will store the synthesis area result for each data width.
    area = []
    # Loop through the data widths again, this time to run the synthesis flow for each one.
    for n in datawidths:
        # Add the corresponding RTL fileset to the project for this run.
        # 'clobber=True' ensures we replace the fileset from the previous iteration.
        proj.add_fileset(f"rtl.{n}", clobber=True)
        # Set a unique jobname for each run. This helps in organizing the results
        # and retrieving metrics from the correct run later.
        proj.set("option", "jobname", f"N{n}")

        # Execute the synthesis flow.
        proj.run()

        # After the run, retrieve the 'cellarea' metric from the 'synthesis' step.
        # We use the jobname to access the history of the specific run we just completed.
        area.append(proj.history(f"N{n}").get('metric', 'cellarea', step='synthesis', index='0'))

    # --- Plotting and Reporting Results ---
    # Check if matplotlib was successfully imported.
    if plt:
        # Create a plot of data width vs. cell area.
        plt.subplots(1, 1)
        plt.plot(datawidths, area, marker='o')
        plt.xlabel("Datawidth (N)")
        plt.ylabel("Cell Area")
        plt.title("Adder Area vs. Datawidth")
        plt.grid(True)
        # Display the plot.
        plt.show()
    else:
        # If matplotlib is not available, print the results to the console
        # and suggest installing it for a visual plot.
        proj.logger.info(f'Datawidths: {datawidths}')
        proj.logger.info(f'Areas: {area}')
        proj.logger.warning('Install matplotlib (`pip install matplotlib`) '
                            'to automatically plot this data!')
        return area


if __name__ == '__main__':
    # Run the main function when the script is executed.
    main()
