.. _docker:

Using SiliconCompiler with Docker
=================================

To run SiliconCompiler flows using our pre-built Docker image, you first need to have Docker installed and running on your system.

1. Install Docker Desktop
-------------------------

The first step is to install Docker Desktop, which provides an easy-to-use environment for managing containers.
Please follow the official installation instructions for your operating system:

* `Install on Linux <https://docs.docker.com/desktop/setup/install/linux/>`_
* `Install on Windows <https://docs.docker.com/desktop/setup/install/windows-install/>`_
* `Install on macOS <https://docs.docker.com/desktop/setup/install/mac-install/>`_

After installation, start Docker Desktop. We recommend using the default settings when prompted.

2. Set Up Your Project
----------------------

Next, open your preferred command-line terminal and run the commands below that correspond to your operating system.
These commands will create a Python virtual environment, activate it, and install siliconcompiler.

Linux / macOS
^^^^^^^^^^^^^
On a standard terminal (`bash` or `zsh`):

.. code-block:: bash

    # Create and activate a Python virtual environment
    python3 -m venv .venv
    source .venv/bin/activate

    # Install SiliconCompiler
    pip install siliconcompiler

Windows
^^^^^^^
On a PowerShell terminal:

# Create and activate a Python virtual environment

.. code-block:: shell

    python3 -m venv .venv
    .venv\Scripts\activate

    # Install SiliconCompiler
    pip install siliconcompiler

3. Run a Test Compilation
-------------------------
With your environment activated and SiliconCompiler installed, you can test your setup by running a simple compilation that uses the Docker scheduler. This command will automatically pull the necessary Docker image and run the flow inside a container.

Execute the following command in the same terminal:

.. code-block:: bash

    sc -target asic_demo -scheduler docker

If the setup is successful, you will see compilation output in your terminal as SiliconCompiler executes the demonstration flow.