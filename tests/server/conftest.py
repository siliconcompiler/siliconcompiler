import pytest


@pytest.fixture
def gcd_remote_test(gcd_chip, scserver, scserver_credential):
    def setup(use_slurm=False):
        # Start running an sc-server instance.
        cluster = "local"
        if use_slurm:
            cluster = "slurm"
        port = scserver(cluster=cluster)

        # Create the temporary credentials file, and set the Chip to use it.
        gcd_chip.set('option', 'credentials', scserver_credential(port))
        gcd_chip.set('option', 'remote', True)

        gcd_chip.set('option', 'nodisplay', True)

        return gcd_chip

    return setup
