# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization

import aiohttp
import asyncio
import base64
import math
import json
import os
import shutil
import subprocess
import sys

###################################
def remote_preprocess(chips):
    '''Helper method to run a local import stage for remote jobs.
    '''

    # Run the local 'import' step.
    chips[-1].run(start='import', stop='import')

    # Clear the 'option' value, in case the import step is run again later.
    chips[-1].cfg['flow']['import']['option']['value'] = []

###################################
def client_decrypt(chip):
    '''Helper method to decrypt project data before running a job on it.
    '''

    root_dir = chip.get('dir')[-1]
    job_nameid = chip.get('jobname')[-1] + chip.get('jobid')[-1]

    # Create cipher for decryption.
    dk = base64.urlsafe_b64decode(chip.status['decrypt_key'])
    decrypt_key = serialization.load_ssh_private_key(dk, None, backend=default_backend())
    # Decrypt the block cipher key.
    with open('%s/import.bin'%root_dir, 'rb') as f:
        aes_key = decrypt_key.decrypt(
            f.read(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

    # Read in the iv nonce.
    with open('%s/%s.iv'%(root_dir, job_nameid), 'rb') as f:
        aes_iv = f.read()

    # Decrypt .crypt file using the decrypted block cipher key.
    job_crypt = '%s/%s.crypt'%(root_dir, job_nameid)
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    decryptor = cipher.decryptor()
    # Same approach as encrypting: open both files, read/decrypt/write individual chunks.
    with open('%s/%s.zip'%(root_dir, job_nameid), 'wb') as wf:
        with open(job_crypt, 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(decryptor.update(chunk))
        wf.write(decryptor.finalize())

    # Unzip the decrypted file to prepare for running the job.
    subprocess.run(['mkdir',
                    '-p',
                    '%s/%s/%s'%(root_dir, chip.get('design')[-1], job_nameid)])
    subprocess.run(['unzip',
                    '-o',
                    '%s/%s.zip'%(root_dir, job_nameid)],
                   cwd='%s/%s/%s'%(root_dir, chip.get('design')[-1], job_nameid))

###################################
def client_encrypt(chip):
    '''Helper method to re-encrypt project data after processing.
    '''

    root_dir = chip.get('dir')[-1]
    job_nameid = chip.get('jobname')[-1] + chip.get('jobid')[-1]

    # Create cipher for decryption.
    dk = base64.urlsafe_b64decode(chip.status['decrypt_key'])
    decrypt_key = serialization.load_ssh_private_key(dk, None, backend=default_backend())
    # Decrypt the block cipher key.
    with open('%s/import.bin'%root_dir, 'rb') as f:
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
                    '-y',
                    '%s.zip'%job_nameid,
                    '.'],
                   cwd='%s/%s/%s'%(root_dir, chip.get('design')[-1], job_nameid))

    # Create a new initialization vector and write it to a file for future decryption.
    # The iv does not need to be secret, but using the same iv and key to encrypt
    # different data can provide an attack surface to potentially decrypt some data.
    aes_iv  = os.urandom(16)
    with open('%s/%s.iv'%(root_dir, job_nameid), 'wb') as f:
        f.write(aes_iv)

    # Encrypt the new zip file.
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
    encryptor = cipher.encryptor()
    with open('%s/%s.crypt'%(root_dir, job_nameid), 'wb') as wf:
        with open('%s/%s/%s/%s.zip'%(root_dir, chip.get('design')[-1], job_nameid, job_nameid), 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(encryptor.update(chunk))
        # Write out any remaining data; CTR mode does not require padding.
        wf.write(encryptor.finalize())

    # Delete decrypted data.
    shutil.rmtree('%s/%s/%s'%(root_dir, chip.get('design')[-1], job_nameid))
    os.remove('%s/%s.zip'%(root_dir, job_nameid))

###################################
def get_remote_hostclass(chip):
    '''Helper method to find a cloud hostclass that matches the given settings.
       If the 'threads' and 'ram' options are both provided, a suitable host
       will be chosen with values up to one power of two above the requested
       ones. Requesting 8GiB of RAM will only look for hosts with 8GiB,
       but requesting 10GiB would look for hosts in the range of 10-16GiB.
       If only one parameter is provided, a host will be chosen with the
       smallest available value for the other parameter.
       If neither parameter is provided, the smallest host type will be used.
    '''

    # Define a matrix of available host configurations.
    # TODO: Import from a JSON file?
    # TODO: Use a newer line of AWS hosts. m4, c5, r5, or even t3 could work.
    hosts = {
        't2.small': {'ram': 2, 'threads': 1},
        't2.medium': {'ram': 4, 'threads': 2},
        't2.large': {'ram': 8, 'threads': 2},
        't2.xlarge': {'ram': 16, 'threads': 4},
        't2.2xlarge': {'ram': 32, 'threads': 8},
    }

    # Set min/max parameters from the chip config, with default fallbacks.
    if len(chip.get('remote', 'ram')) > 0:
        ram_min = int(chip.get('remote', 'ram')[-1])
        ram_max = math.pow(2, int(math.log2(ram_min)))
    else:
        ram_min = 2
        ram_max = 32
    if len(chip.get('remote', 'threads')) > 0:
        threads_min = int(chip.get('remote', 'threads')[-1])
        threads_max = math.pow(2, int(math.log2(threads_min)))
    else:
        threads_min = 1
        threads_max = 8

    # Pick the smallest host that matches the given configs.
    # Prioritise threads when comparing.
    cur_host = ''
    for host_key, host in hosts.items():
        if (host['ram'] >= ram_min) and (host['ram'] <= ram_max) and \
           (host['threads'] >= threads_min) and (host['threads'] <= threads_max):
            if (cur_host == '') or \
               (hosts[cur_host]['threads'] < host['threads']) or \
               ((hosts[cur_host]['threads'] == host['threads']) and \
                (hosts[cur_host]['ram'] < host['ram'])):
                cur_host = host_key

    # Done, return the generated host type.
    return cur_host

###################################
async def remote_run(chip, stage):
    '''Helper method to run a job stage on a remote compute cluster.
    Note that files will not be copied to the remote stage; typically
    the source files will be copied into the cluster's storage before
    calling this method.
    If the "-remote" parameter was not passed in, this method
    will print a warning and do nothing.
    This method assumes that the given stage should not be skipped,
    because it is called from within the `Chip.run(...)` method.

    '''

    # Ask the remote server to start processing the requested step.
    chip.cfg['start']['value'] = [stage]
    chip.cfg['stop']['value'] = [stage]
    await request_remote_run(chip, stage)

    # Check the job's progress periodically until it finishes.
    is_busy = True
    while is_busy:
      print("%s stage running. Please wait."%stage)
      await asyncio.sleep(1)
      is_busy = await is_job_busy(chip, stage)
    print("%s stage completed!"%stage)

###################################
async def request_remote_run(chip, stage):
    '''Helper method to make an async request to start a job stage.

    '''
    async with aiohttp.ClientSession() as session:
        remote_run_url = "http://%s:%s/remote_run/"%(
                         chip.cfg['remote']['addr']['value'][-1],
                         chip.cfg['remote']['port']['value'][-1])

        # Use authentication if necessary.
        post_params = {'chip_cfg': chip.cfg}
        if (len(chip.get('remote', 'user')) > 0) and (len(chip.get('remote', 'key')) > 0):
            # Read the key and encode it in base64 format.
            with open(os.path.abspath(chip.cfg['remote']['key']['value'][-1]), 'rb') as f:
                key = f.read()
            b64_key = base64.urlsafe_b64encode(key).decode()
            post_params['params'] = {
                'username': chip.get('remote', 'user')[-1],
                'key': b64_key,
                'job_hash': chip.status['job_hash'],
                'stage': stage,
            }
        else:
            post_params['params'] = {
                'job_hash': chip.status['job_hash'],
                'stage': stage,
            }

        # Make the actual request.
        async with session.post(remote_run_url, json=post_params) as resp:
            print(await resp.text())

###################################
async def is_job_busy(chip, stage):
    '''Helper method to make an async request asking the remote server
    whether a job is busy, or ready to accept a new step.
    Returns True if the job is busy, False if not.

    '''

    async with aiohttp.ClientSession() as session:
        # Set common parameters.
        post_params = {
            'job_hash': chip.status['job_hash'],
            'job_id': chip.get('jobid')[-1],
        }

        # Set authentication parameters if necessary.
        if (len(chip.get('remote', 'user')) > 0) and (len(chip.get('remote', 'key')) > 0):
            with open(os.path.abspath(chip.cfg['remote']['key']['value'][-1]), 'rb') as f:
                key = f.read()
            b64_key = base64.urlsafe_b64encode(key).decode()
            post_params['username'] = chip.get('remote', 'user')[-1]
            post_params['key'] = b64_key

        # Make the request and print its response.
        async with session.post("http://%s:%s/check_progress/"%(
                                chip.cfg['remote']['addr']['value'][-1],
                                chip.cfg['remote']['port']['value'][-1]),
                                json=post_params) \
        as resp:
            response = await resp.text()
            return (response != "Job has no running steps.")

###################################
async def delete_job(chip):
    '''Helper method to delete a job from shared remote storage.
    '''

    async with aiohttp.ClientSession() as session:
        # Set common parameter.
        post_params = {
            'job_hash': chip.status['job_hash'],
        }

        # Set authentication parameters if necessary.
        if (len(chip.get('remote', 'user')) > 0) and (len(chip.get('remote', 'key')) > 0):
            with open(os.path.abspath(chip.cfg['remote']['key']['value'][-1]), 'rb') as f:
                key = f.read()
            b64_key = base64.urlsafe_b64encode(key).decode()
            post_params['username'] = chip.get('remote', 'user')[-1]
            post_params['key'] = b64_key

        # Make the request.
        async with session.post("http://%s:%s/delete_job/"%(
                               chip.cfg['remote']['addr']['value'][-1],
                               chip.cfg['remote']['port']['value'][-1]),
                               json=post_params) \
        as resp:
            response = await resp.text()
            return response

###################################
async def upload_import_dir(chip):
    '''Helper method to make an async request uploading the post-import
    files to the remote compute cluster.
    '''

    async with aiohttp.ClientSession() as session:
        post_params = {
            'job_hash': chip.status['job_hash'],
            'job_name': chip.get('jobname')[-1],
            'job_ids': chip.status['perm_ids'],
        }
        if (len(chip.get('remote', 'user')) > 0) and (len(chip.get('remote', 'key')) > 0):
            # Encrypt the .zip archive with the user's public key.
            # Asymmetric key cryptography is good at signing values, but bad at
            # encrypting bulk data. One common approach is to generate a random
            # symmetric encryption key, which can be encrypted using the asymmetric
            # keys. Then the data itself can be encrypted with the symmetric cipher.
            # We'll use AES-256-CTR, because the Python 'cryptography' module's
            # recommended 'Fernet' algorithm only works on files that fit in memory.

            # Generate AES key and iv nonce.
            aes_key = os.urandom(32)
            aes_iv  = os.urandom(16)

            # Read in the user's public key.
            # TODO: This assumes a common OpenSSL convention of using similar file
            # paths for private and public keys: /path/to/key and /path/to/key.pub
            # If the user has the account's private key, it is assumed that they
            # will also have the matching public key in the same locale.
            with open('%s.pub'%os.path.abspath(chip.get('remote', 'key')[-1]), 'r') as f:
                encrypt_key = serialization.load_ssh_public_key(
                    f.read().encode(),
                    backend=default_backend())
            # Encrypt the AES key using the user's public key.
            # (The IV nonce can be stored in plaintext)
            aes_key_enc = encrypt_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA512()),
                    algorithm=hashes.SHA512(),
                    label=None,
                ))

            # Create the AES cipher.
            cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
            encryptor = cipher.encryptor()

            # Open both 'import.zip' and 'import.crypt' files.
            # We're using a stream cipher to support large files which may not fit
            # in memory, so we'll read and write data one 'chunk' at a time.
            with open('import.crypt', 'wb') as wf:
                with open('import.zip', 'rb') as rf:
                    while True:
                        chunk = rf.read(1024)
                        if not chunk:
                            break
                        wf.write(encryptor.update(chunk))
                # Write out any remaining data; CTR mode does not require padding.
                wf.write(encryptor.finalize())

            # Set up encryption and authentication parameters in the request body.
            with open(os.path.abspath(chip.cfg['remote']['key']['value'][-1]), 'rb') as f:
                key = f.read()
            b64_key = base64.urlsafe_b64encode(key).decode()
            post_params['username'] = chip.get('remote', 'user')[-1]
            post_params['key'] = b64_key
            post_params['aes_key'] = base64.urlsafe_b64encode(aes_key_enc).decode()
            post_params['aes_iv'] = base64.urlsafe_b64encode(aes_iv).decode()
            num_temp_hosts = int(chip.get('remote', 'hosts')[-1])
            if num_temp_hosts > 0:
                post_params['new_hosts'] = num_temp_hosts
                post_params['new_host_type'] = get_remote_hostclass(chip)
                if not post_params['new_host_type']:
                    chip.logger.error('Unable to find a cloud host type matching the requested configuration.')
                    sys.exit(1)
            # Upload the encrypted file.
            upload_file = os.path.abspath('import.crypt')

        else:
            # No authorizaion configured; upload the unencrypted archive.
            upload_file = os.path.abspath('import.zip')

        # Make the 'import' API call and print the response.
        with open(upload_file, 'rb') as f:
            async with session.post("http://%s:%s/import/"%(
                                        chip.cfg['remote']['addr']['value'][-1],
                                        chip.cfg['remote']['port']['value'][-1]),
                                    data={'import': f,
                                          'params': json.dumps(post_params)}) \
            as resp:
                print(await resp.text())

###################################
def upload_sources_to_cluster(chip):
    '''Helper method to upload Verilog source files to a cloud compute
    cluster's shared storage. Required before the cluster will be able
    to run any job steps.

    TODO: This method will shortly be replaced with a server call.

    '''

    # Zip the 'import' directory.
    # TODO: Encrypted jobs need to start one level up, this should be unified though.
    if (len(chip.get('remote', 'user')) > 0) and (len(chip.get('remote', 'key')) > 0):
        subprocess.run(['zip',
                        '-r',
                        'import/import.zip',
                        'import'],
                       cwd='..')
    else:
        subprocess.run(['zip',
                        '-r',
                        'import.zip',
                        '.'])

    # Upload the archive to the 'import' server endpoint.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(upload_import_dir(chip))

###################################
async def fetch_results_request(chips):
    '''Helper method to fetch job results from a remote compute cluster.
    '''

    async with aiohttp.ClientSession() as session:
        job_hash = chips[-1].status['job_hash']

        # Set authentication parameters if necessary.
        if (len(chips[-1].get('remote', 'user')) > 0) and (len(chips[-1].get('remote', 'key')) > 0):
            with open(os.path.abspath(chips[-1].cfg['remote']['key']['value'][-1]), 'rb') as f:
                key = f.read()
            b64_key = base64.urlsafe_b64encode(key).decode()
            post_params = {
                'username': chips[-1].get('remote', 'user')[-1],
                'key': b64_key,
            }
        else:
            post_params = {}

        # Make the web request, and stream the results archive in chunks.
        with open('%s.zip'%job_hash, 'wb') as zipf:
            async with session.post("http://%s:%s/get_results/%s.zip"%(
                                    chips[-1].cfg['remote']['addr']['value'][-1],
                                    chips[-1].cfg['remote']['port']['value'][-1],
                                    job_hash),
                                    json = post_params) \
            as resp:
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break
                    zipf.write(chunk)

###################################
def fetch_results(chips):
    '''Helper method to fetch and open job results from a remote compute cluster.
    '''

    # Fetch the remote archive after the export stage.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(fetch_results_request(chips))

    # Unzip the results.
    job_hash = chips[-1].status['job_hash']
    subprocess.run(['unzip', '%s.zip'%job_hash])

    # Call 'delete_job' to remove the run from the server.
    # This deletes a job_hash, so separate calls for each permutation are not required.
    loop.run_until_complete(delete_job(chips[-1]))

    # For encrypted jobs each permutation's result is encrypted in its own archive.
    # For unencrypted jobs, results are simply stored in the archive.
    if len(chips[-1].get('remote', 'key')) > 0:
        # Decrypt the block cipher key using the user's private key.
        with open('%s/import.bin'%job_hash, 'rb') as f:
            aes_key_enc = f.read()
        with open('%s'%os.path.abspath(chips[-1].get('remote', 'key')[-1]), 'r') as f:
            decrypt_key = serialization.load_ssh_private_key(
                f.read().encode(),
                None,
                backend=default_backend())
        aes_key = decrypt_key.decrypt(
            aes_key_enc,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA512()),
                algorithm=hashes.SHA512(),
                label=None,
            ))

        # Decrypt each permutation using their individual initialization vectors.
        for chip in chips:
            # Read in the iv.
            job_nameid = chip.get('jobname')[-1] + chip.get('jobid')[-1]
            with open('%s/%s.iv'%(job_hash, job_nameid), 'rb') as f:
                aes_iv = f.read()

            # Create the AES cipher.
            cipher = Cipher(algorithms.AES(aes_key), modes.CTR(aes_iv))
            decryptor = cipher.decryptor()

            # Decrypt the '.crypt' file in chunks.
            with open('%s/%s.zip'%(job_hash, job_nameid), 'wb') as wf:
                with open('%s/%s.crypt'%(job_hash, job_nameid), 'rb') as rf:
                    while True:
                        chunk = rf.read(1024)
                        if not chunk:
                            break
                        wf.write(decryptor.update(chunk))
                # Write out any remaining data; CTR mode does not require padding.
                wf.write(decryptor.finalize())

            # Unzip the decrypted archive in the 'job_hash' working directory.
            perm_dir = '%s/%s'%(chip.get('design')[-1], job_nameid)
            subprocess.run(['mkdir', '-p', perm_dir], cwd=job_hash)
            subprocess.run(['unzip', '-d', perm_dir, '%s.zip'%job_nameid], cwd=job_hash)

    # Wildcard filepath which should cover all GDS files.
    gds_loc = '%s/%s/%s*/export/outputs/%s.gds'%(
        job_hash,
        chips[-1].cfg['design']['value'][-1],
        chips[-1].cfg['jobname']['value'][-1],
        chips[-1].cfg['design']['value'][-1],
    )
    # Done; display the results using klayout.
    subprocess.run(['klayout', gds_loc])
