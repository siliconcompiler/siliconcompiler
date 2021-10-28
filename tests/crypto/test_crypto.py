# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os

from siliconcompiler.client import *
from siliconcompiler.crypto import *

def test_crypto(scroot):
    crypto_key = os.path.join(scroot, 'tests', 'data', 'insecure_ci_keypair')

    # Create a directory structure representing a job run.
    os.mkdir('build')
    os.mkdir('build/test')
    os.mkdir('build/test/job0')
    os.mkdir('build/test/job0/import0')
    test_msg = 'This file will be encrypted.'
    with open('build/test/job0/import0/test_file', 'w') as f:
        f.write(test_msg)

    # Create an encrypted block cipher key for the job to use.
    gen_cipher_key('build/test/job0', f'{crypto_key}.pub')

    # Encrypt the example data, and ensure that it is no longer on disk.
    encrypt_job('build/test/job0', crypto_key)
    assert not os.path.isfile('build/test/job0/import0/test_file')
    assert not os.path.isdir('build/gcd/job0/import0')

    # Ensure that the example data can be decrypted successfully.
    decrypt_job('build/test/job0', crypto_key)
    assert os.path.isfile('build/test/job0/import0/test_file')
    with open('build/test/job0/import0/test_file', 'r') as f:
        assert test_msg == f.read()

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_crypto(scroot())
