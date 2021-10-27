# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization

import argparse
import json
import os
import shutil
import subprocess
import sys

def gen_cipher_key(gen_dir, pubk_filestr, pubk_type='file'):
    # Create the key (32 random bytes = a 256-bit AES block cipher key)
    aes_key = os.urandom(32)

    # Use the public key file to encrypt the cipher key.
    if pubk_type == 'file':
        with open(pubk_filestr, 'r') as f:
            encrypt_key = serialization.load_ssh_public_key(
                f.read().encode(),
                backend=default_backend())
    else:
        encrypt_key = serialization.load_ssh_public_key(
            pubk_filestr.encode(),
            backend=default_backend())
    aes_key_enc = encrypt_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA512()),
            algorithm=hashes.SHA512(),
            label=None,
        ))

    with open(os.path.join(gen_dir, 'import.bin'), 'wb') as f:
        f.write(aes_key_enc)

def write_encrypted_cfgfile(cfg, job_dir, pk_bytes, file_prefix):
    # Helper method to write an encrypted config file to disk.
    # Unlike most of these methods, this accepts the private key's bytes
    # instead of a filename. It is intended to be used on a server with a shared
    # disk, to help ensure that sensitive decrypted data is kept in RAM.

    # Collect some basic values.
    top_dir = os.path.abspath(os.path.join(job_dir, '..', '..'))

    # Create cipher for decryption.
    decrypt_key = serialization.load_ssh_private_key(pk_bytes, None, backend=default_backend())

    # Decrypt the block cipher key.
    with open(os.path.join(job_dir, 'import.bin'), 'rb') as f:
        aes_key = decrypt_key.decrypt(
            f.read(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

    # Create the 'configs/' directory to write into, if it doesn't exist already.
    if not os.path.isdir(os.path.join(job_dir, 'configs')):
        os.mkdir(os.path.join(job_dir, 'configs'))

    # Create a new initialization vector and write it to a file for future decryption.
    # The iv does not need to be secret, but using the same iv and key to encrypt
    # different data can provide an attack surface to potentially decrypt some data.
    aes_iv  = os.urandom(16)
    with open(os.path.join(job_dir, 'configs', f'{file_prefix}.iv'), 'wb') as f:
        f.write(aes_iv)

    # Encrypt the JSON config and write it to disk under a 'configs/' directory.
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    encryptor = cipher.encryptor()
    with open(os.path.join(job_dir, 'configs', f'{file_prefix}.crypt'), 'wb') as wf:
        # Write the config dictionary's JSON contents through the encryptor.
        cfg_bytes = json.dumps(cfg, indent=4, sort_keys=True).encode()
        wf.write(encryptor.update(cfg_bytes))
        # Write out any remaining data; CTR mode does not require padding.
        wf.write(encryptor.finalize())

def encrypt_job(job_dir, pk_filestr, pk_type='file'):
    # Find a list of {step}{index} directories. Use 'next' to avoid recursion.
    (root, dirs, files) = next(os.walk(job_dir))
    # Encrypt each directory individually.
    for enc_dir in dirs:
        encrypt_dir(os.path.join(job_dir, enc_dir), pk_filestr, pk_type)

def encrypt_dir(enc_dir, pk_filestr, pk_type='file'):
    # Collect some basic values.
    job_dir = os.path.abspath(os.path.join(enc_dir, '..'))
    top_dir = os.path.abspath(os.path.join(job_dir, '..', '..'))
    stepname = os.path.split(enc_dir)[-1]

    # Create cipher for decryption.
    if pk_type == 'file':
        with open(pk_filestr, 'r') as keyin:
            dk = keyin.read().encode()
    else:
        dk = pk_filestr.encode()
    decrypt_key = serialization.load_ssh_private_key(dk, None, backend=default_backend())

    # Decrypt the block cipher key.
    with open(os.path.join(job_dir, 'import.bin'), 'rb') as f:
        aes_key = decrypt_key.decrypt(
            f.read(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

    # Zip the step directory.
    if not os.path.isdir(enc_dir):
        os.makedirs(enc_dir)
    if os.path.isfile(os.path.join(enc_dir, f'{stepname}.zip')):
        os.remove(os.path.join(enc_dir, f'{stepname}.zip'))
    subprocess.run(['tar',
                    '-cf',
                    f'{stepname}.zip',
                    '.'],
                   cwd=enc_dir)

    # Create a new initialization vector and write it to a file for future decryption.
    # The iv does not need to be secret, but using the same iv and key to encrypt
    # different data can provide an attack surface to potentially decrypt some data.
    aes_iv  = os.urandom(16)
    with open(os.path.join(job_dir, f'{stepname}.iv'), 'wb') as f:
        f.write(aes_iv)

    # Encrypt the new zip file.
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    encryptor = cipher.encryptor()
    with open(os.path.join(job_dir, f'{stepname}.crypt'), 'wb') as wf:
        with open(os.path.join(enc_dir, f'{stepname}.zip'), 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(encryptor.update(chunk))
        # Write out any remaining data; CTR mode does not require padding.
        wf.write(encryptor.finalize())

    # Delete decrypted data.
    shutil.rmtree(f'{enc_dir}')
    if os.path.isfile(os.path.join(job_dir, f'{stepname}.zip')):
        os.remove(os.path.join(job_dir, f'{stepname}.zip'))

def decrypt_cfgfile(crypt_file, pk_file):
    # Helper method to decrypt an encrypted Chip configuration file.
    job_dir = os.path.dirname(crypt_file)
    top_dir = os.path.abspath(os.path.join(job_dir, '..', '..'))
    file_prefix = os.path.split(crypt_file)[-1].split('.crypt')[0]

    # Create cipher for decryption.
    with open(pk_file, 'r') as keyin:
        dk = keyin.read().encode()
    decrypt_key = serialization.load_ssh_private_key(dk, None, backend=default_backend())

    # Decrypt the block cipher key, which should be one dir up from the cfg file.
    with open(os.path.join(job_dir, '..', 'import.bin'), 'rb') as f:
        aes_key = decrypt_key.decrypt(
            f.read(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

    # Read in the iv nonce.
    with open(os.path.join(job_dir, f'{file_prefix}.iv'), 'rb') as f:
        aes_iv = f.read()

    # Decrypt .crypt file using the decrypted block cipher key.
    job_crypt = os.path.join(job_dir, f'{file_prefix}.crypt')
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    decryptor = cipher.decryptor()
    # Same approach as encrypting: open both files, read/decrypt/write individual chunks.
    with open(os.path.join(job_dir, f'{file_prefix}.json'), 'wb') as wf:
        with open(job_crypt, 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(decryptor.update(chunk))
        wf.write(decryptor.finalize())

def decrypt_job(job_dir, pk_filestr, pk_type='file'):
    # Find a list of {step}{index} encrypted dirs. Use 'next' to avoid recursion.
    (root, dirs, files) = next(os.walk(job_dir))
    # Decrypt each directory individually.
    for crypt_file in files:
        if crypt_file[-6:] == '.crypt':
            if os.path.isfile(os.path.join(job_dir, f'{crypt_file[:-6]}.iv')):
                decrypt_dir(os.path.join(job_dir, crypt_file), pk_filestr, pk_type)

def decrypt_dir(crypt_file, pk_filestr, pk_type='file'):
    # Collect some basic values.
    job_dir = os.path.dirname(crypt_file)
    top_dir = os.path.abspath(os.path.join(job_dir, '..', '..'))
    stepname = os.path.split(crypt_file)[-1].split('.crypt')[0]
    step_dir = os.path.join(job_dir, stepname)

    # Create cipher for decryption.
    if pk_type == 'file':
        with open(pk_filestr, 'r') as keyin:
            dk = keyin.read().encode()
    else:
        dk = pk_filestr.encode()
    decrypt_key = serialization.load_ssh_private_key(dk, None, backend=default_backend())

    # Decrypt the block cipher key.
    with open(os.path.join(job_dir, 'import.bin'), 'rb') as f:
        aes_key = decrypt_key.decrypt(
            f.read(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

    # Read in the iv nonce.
    with open(os.path.join(job_dir, f'{stepname}.iv'), 'rb') as f:
        aes_iv = f.read()

    # Decrypt .crypt file using the decrypted block cipher key.
    job_crypt = os.path.join(job_dir, f'{stepname}.crypt')
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    decryptor = cipher.decryptor()
    # Same approach as encrypting: open both files, read/decrypt/write individual chunks.
    with open(os.path.join(job_dir, f'{stepname}.zip'), 'wb') as wf:
        with open(job_crypt, 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(decryptor.update(chunk))
        wf.write(decryptor.finalize())

    # Unzip the decrypted file to prepare for running the job (if necessary).
    os.makedirs(step_dir)
    subprocess.run(['tar',
                    '-xf',
                    os.path.abspath(os.path.join(job_dir, f'{stepname}.zip'))],
                   cwd=step_dir)

# Provide a way to encrypt/decrypt from the command line. (With the correct key)
# This is mostly intended to make it easier to run individual job steps in an
# HPC cluster when the data needs to be encrypted 'at rest'. It should not be
# necessary to run these steps manually in a normal workflow.
def main():
    #Argument Parser
    parser = argparse.ArgumentParser(prog='sc-crypt',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection Encrypt / Decrypt Utility")

    # Command-line options (all required):
    parser.add_argument('-mode', required=True)
    parser.add_argument('-target', required=True)
    parser.add_argument('-key_file', required=True)

    # Parse arguments.
    cmdargs = vars(parser.parse_args())

    # Check for invalid parameters.
    if (not cmdargs['mode'] in ['encrypt', 'decrypt', 'decrypt_config']) or \
       (not os.path.exists(cmdargs['target'])) or \
       (not os.path.isfile(cmdargs['key_file'])):
        print('Error: Invalid command-line parameters.', file=sys.stderr)
        sys.exit(1)

    # Perform the encryption or decryption.
    if cmdargs['mode'] == 'encrypt':
        encrypt_job(cmdargs['target'], cmdargs['key_file'])
    elif cmdargs['mode'] == 'decrypt':
        decrypt_job(cmdargs['target'], cmdargs['key_file'])
    elif cmdargs['mode'] == 'decrypt_config':
        decrypt_cfgfile(cmdargs['target'], cmdargs['key_file'])

if __name__ == "__main__":
    main()
