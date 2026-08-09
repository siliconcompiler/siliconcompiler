.. _docker:

Using SiliconCompiler with Docker
=================================

To run SiliconCompiler flows using our pre-built Docker image, you first need to have Docker installed and running on your system.

.. _docker_two_ways:

Two ways to use the image
-------------------------

The same image, ``ghcr.io/siliconcompiler/sc_runner``, is used in two different
ways, and they are easy to confuse because both are "running SiliconCompiler in
Docker". They differ in *what* goes in the container:

.. list-table::
   :header-rows: 1
   :widths: 16 42 42

   * -
     - Docker **scheduler**
     - ``docker run`` **the whole script**
   * - Looks like
     - ``project.option.scheduler.set_name("docker")``, or ``-scheduler docker``
     - ``docker run --rm -v "$(pwd):/sc_work" ghcr.io/siliconcompiler/sc_runner:latest python3 make.py``
   * - What runs in the container
     - Each :term:`flowgraph node` -- one container per node, started and stopped
       by SiliconCompiler
     - Everything, including SiliconCompiler itself -- one container for the run
   * - What runs on your machine
     - SiliconCompiler, in your own Python environment
     - Only Docker
   * - Needs SiliconCompiler installed?
     - Yes (``pip install siliconcompiler``)
     - No
   * - Version you get
     - Yours drives the flow; the image supplies the tools
     - Whatever the image ships

**Use the scheduler** for normal work. You keep your own Python environment, your
own SiliconCompiler version, and the dashboard, while the EDA tools come from the
container -- so there is nothing to install and nothing to keep in sync.

**Use** ``docker run`` when you want to run a script on a machine with nothing
installed but Docker, or to reproduce a result against a pinned image. The
mounted directory (``/sc_work`` above) is where the build tree is written, so
results land in your working directory as usual.

The rest of this page sets up the scheduler.

.. note::
   The scheduler picks its image from :keypath:`option,scheduler,queue` if set,
   then the ``SC_DOCKER_IMAGE`` environment variable, then
   ``ghcr.io/siliconcompiler/sc_runner:v<version>`` matching your installed
   SiliconCompiler. Because ``queue`` is per-node, different steps can run in
   different images.

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

.. code-block:: powershell

    # Create and activate a Python virtual environment
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

    # Install SiliconCompiler
    pip install siliconcompiler

3. Run a Test Compilation
-------------------------
With your environment activated and SiliconCompiler installed, you can test your setup by running a simple compilation that uses the Docker scheduler. This command will automatically pull the necessary Docker image and run the flow inside a container.

Execute the following command in the same terminal:

.. code-block:: bash

    python -m siliconcompiler.demos.asic_demo -scheduler docker

If the setup is successful, you will see compilation output in your terminal as SiliconCompiler executes the demonstration flow.