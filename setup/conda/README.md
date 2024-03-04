# Environment and Tool Setup Using Conda

The [conda-eda project](https://github.com/hdl/conda-eda) provides recipes for installing many core open-source EDA tools using the Anaconda / Miniconda Python package management system.

We would like to fully support this avenue of setting up a development environment, but the process currently requires a few steps outside of Conda. In the future, we hope to provide a siliconcompiler Conda recipe which can be used seamlessly with this environment.

For now, a few steps are required to create a development environment using Conda:

* Create and activate the Conda environment:

    conda env create -f environment.yml
    conda activate sc_env

We believe that this setup process will only work on Linux systems at this time.
