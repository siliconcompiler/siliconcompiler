# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization

import argparse
import os
import shutil
import subprocess
import sys

def gen_cipher_key(gen_dir, pubk_file):
    # Create the key (32 random bytes = a 256-bit AES block cipher key)
    aes_key = os.urandom(32)

    # Use the public key file to encrypt the cipher key.
    with open(pubk_file, 'r') as f:
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

    with open(f'{gen_dir}/import.bin', 'wb') as f:
        f.write(aes_key_enc)

def encrypt_job(job_dir, pk_file):
    # Collect some basic values.
    top_dir = os.path.abspath(f'{job_dir}/../..')
    job_dirname = os.path.abspath(job_dir).split('/')[-1]

    # Create cipher for decryption.
    with open(pk_file, 'r') as keyin:
        dk = keyin.read().encode()
    decrypt_key = serialization.load_ssh_private_key(dk, None, backend=default_backend())

    # Decrypt the block cipher key.
    with open(f'{top_dir}/import.bin', 'rb') as f:
        aes_key = decrypt_key.decrypt(
            f.read(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

    # Zip the new job results.
    subprocess.run(['zip',
                    '-r',
                    f'{job_dirname}.zip',
                    '.'],
                   cwd=job_dir)

    # Create a new initialization vector and write it to a file for future decryption.
    # The iv does not need to be secret, but using the same iv and key to encrypt
    # different data can provide an attack surface to potentially decrypt some data.
    aes_iv  = os.urandom(16)
    with open(f'{top_dir}/{job_dirname}.iv', 'wb') as f:
        f.write(aes_iv)

    # Encrypt the new zip file.
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    encryptor = cipher.encryptor()
    with open(f'{top_dir}/{job_dirname}.crypt', 'wb') as wf:
        with open(f'{job_dir}/{job_dirname}.zip', 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(encryptor.update(chunk))
        # Write out any remaining data; CTR mode does not require padding.
        wf.write(encryptor.finalize())

    # Delete decrypted data.
    shutil.rmtree(f'{job_dir}')
    if os.path.isfile(f'{top_dir}/{job_dirname}.zip'):
        os.remove(f'{top_dir}/{job_dirname}.zip')

def decrypt_job(job_dir, pk_file):
    # Collect some basic values.
    top_dir = os.path.abspath(f'{job_dir}/../..')
    job_dirname = os.path.abspath(job_dir).split('/')[-1]

    # Create cipher for decryption.
    with open(pk_file, 'r') as keyin:
        dk = keyin.read().encode()
    decrypt_key = serialization.load_ssh_private_key(dk, None, backend=default_backend())

    # Decrypt the block cipher key.
    with open(f'{top_dir}/import.bin', 'rb') as f:
        aes_key = decrypt_key.decrypt(
            f.read(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

    # Read in the iv nonce.
    with open(f'{top_dir}/{job_dirname}.iv', 'rb') as f:
        aes_iv = f.read()

    # Decrypt .crypt file using the decrypted block cipher key.
    job_crypt = f'{top_dir}/{job_dirname}.crypt'
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    decryptor = cipher.decryptor()
    # Same approach as encrypting: open both files, read/decrypt/write individual chunks.
    with open(f'{top_dir}/{job_dirname}.zip', 'wb') as wf:
        with open(job_crypt, 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(decryptor.update(chunk))
        wf.write(decryptor.finalize())

    # Unzip the decrypted file to prepare for running the job (if necessary).
    subprocess.run(['mkdir',
                    '-p',
                    job_dir])
    subprocess.run(['unzip',
                    '-o',
                    os.path.abspath(f'{top_dir}/{job_dirname}.zip')],
                   cwd=job_dir)

# Provide a way to encrypt/decrypt from the command line. (With the correct key)
# This is mostly intended to make it easier to run individual job steps in an
# HPC cluster when the data needs to be encrypted 'at rest'. It should not be
# necessary to run these steps manually in a normal workflow.
if __name__ == "__main__":
    #Argument Parser
    parser = argparse.ArgumentParser(prog='sc-crypt',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection Encrypt / Decrypt Utility")

    # Command-line options (all required):
    parser.add_argument('-mode', required=True)
    parser.add_argument('-job_dir', required=True)
    parser.add_argument('-key_file', required=True)

    # Parse arguments.
    cmdargs = vars(parser.parse_args())

    # Check for invalid parameters.
    if (not cmdargs['mode'] in ['encrypt', 'decrypt']) or \
       (not os.path.isdir(cmdargs['job_dir'])) or \
       (not os.path.isfile(cmdargs['key_file'])):
        print('Error: Invalid command-line parameters.', file=sys.stderr)
        sys.exit(1)

    # Perform the encryption or decryption.
    if cmdargs['mode'] == 'encrypt':
        encrypt_job(cmdargs['job_dir'], cmdargs['key_file'])
    elif cmdargs['mode'] == 'decrypt':
        decrypt_job(cmdargs['job_dir'], cmdargs['key_file'])
