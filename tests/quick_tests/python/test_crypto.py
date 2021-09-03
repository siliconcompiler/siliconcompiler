# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os

from siliconcompiler import Chip
from siliconcompiler.client import *
from siliconcompiler.crypto import *

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_crypto():
    mydir = os.path.dirname(os.path.abspath(__file__))
    sc_root = f'{mydir}/../../..'
    crypto_key = f'{sc_root}/tests/insecure_ci_keypair'

    # Create a directory structure representing a job run.
    os.mkdir('build')
    os.mkdir('build/test')
    os.mkdir('build/test/job0')
    os.mkdir('build/test/job0/import0')
    os.mkdir('build/test/job0/syn0')
    test_msg = 'This file will be encrypted.'
    with open('build/test/job0/import0/test_file', 'w') as f:
        f.write(test_msg)

    # Create and encrypt AES cipher key for the encryption logic.
    aes_key = os.urandom(32)
    # Use the test public key to encrypt the cipher key.
    with open(f'{crypto_key}.pub', 'r') as f:
        encrypt_key = serialization.load_ssh_public_key(
            f.read().encode(),
            backend=default_backend())
    aes_key_enc = encrypt_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA512()),
            algorithm=hashes.SHA512(),
            label=None,
        ))
    # Write the encrypted key where the sc client would put it.
    with open('build/import.bin', 'wb') as f:
        f.write(aes_key_enc)

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
    test_crypto()
