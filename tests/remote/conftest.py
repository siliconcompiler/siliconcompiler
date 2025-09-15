import pytest


from siliconcompiler import Flowgraph, Project
from siliconcompiler.tools.builtin.nop import NOPTask


@pytest.fixture
def gcd_nop_project(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    project.set_flow(flow)

    project.set('option', 'nodisplay', True)
    project.set('option', 'quiet', True)

    return project


@pytest.fixture
def gcd_remote_test(gcd_nop_project, scserver, scserver_credential):
    def setup(use_slurm=False):
        # Start running an sc-server instance.
        cluster = "local"
        if use_slurm:
            cluster = "slurm"
        port = scserver(cluster=cluster)

        # Create the temporary credentials file, and set the Chip to use it.
        gcd_nop_project.set('option', 'credentials', scserver_credential(port))
        gcd_nop_project.set('option', 'remote', True)

        gcd_nop_project.set('option', 'nodisplay', True)

        return gcd_nop_project

    return setup
