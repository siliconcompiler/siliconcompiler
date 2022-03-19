# Environment and Tool Setup Using Conda

The LiteX project [provides recipes](https://github.com/hdl/conda-eda) for installing many core open-source EDA tools using the Anaconda / Miniconda Python package management system.

We would like to fully support this avenue of setting up a development environment, but the process currently requires a few steps outside of Conda. In the future, we hope to provide a siliconcompiler Conda recipe which can be used seamlessly with this environment.

For now, a few steps are required to create a development environment using Conda:

* Create and activate the Conda environment:

    conda env create -f conda_env.yml
    conda activate sc_env

* Clone the siliconcompiler repository, and set the $SCPATH environment variable so that the `third_party/pdks` directory can be found. You may also want to set $SCPATH in your ~/.bashrc file:

    git clone https://github.com/siliconcompiler/siliconcompiler.git
    export SCPATH=siliconcompiler/siliconcompiler

* Install [KLayout](https://www.klayout.de/build.html) on your system manually.

We believe that this setup process will only work on Linux systems at this time.
