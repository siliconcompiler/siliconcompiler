import pytest
import json
import os


@pytest.fixture
def gcd_remote_test(gcd_chip, scserver):
    def setup(use_slurm=False):
        # Start running an sc-server instance.
        cluster = "local"
        if use_slurm:
            cluster = "slurm"
        port = scserver(cluster=cluster)

        # Create the temporary credentials file, and set the Chip to use it.
        tmp_creds = '.test_remote_cfg'
        with open(tmp_creds, 'w') as tmp_cred_file:
            tmp_cred_file.write(json.dumps({'address': 'localhost',
                                            'port': port}))
        gcd_chip.set('option', 'remote', True)
        gcd_chip.set('option', 'credentials', os.path.abspath(tmp_creds))

        gcd_chip.set('option', 'nodisplay', True)

        return gcd_chip

    return setup
