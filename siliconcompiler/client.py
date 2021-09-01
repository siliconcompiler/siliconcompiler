# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization

import base64
import glob
import math
import multiprocessing
import importlib
import json
import os
import requests
import shutil
import subprocess
import sys
import time
import uuid

###################################
def get_base_url(chip):
    '''Helper method to get the root URL for API calls, given a Chip object.
    '''
    remote_host = chip.get('remote', 'addr')
    remote_port = chip.get('remote', 'port')
    remote_host += ':' + str(remote_port)
    if remote_host.startswith('http'):
        remote_protocol = ''
    else:
        remote_protocol = 'https://' if remote_port == '443' else 'http://'
    return remote_protocol + remote_host

###################################
def remote_preprocess(chip):
    '''Helper method to run a local import stage for remote jobs.
    '''

    # Assign a new 'job_hash' to the chip if necessary.
    if not chip.get('remote', 'jobhash'):
        job_hash = uuid.uuid4().hex
        chip.set('remote', 'jobhash', job_hash)

    # Run any local steps if necessary.
    local_steps = []
    for step in chip.getkeys('flowgraph'):
        if not step in chip.get('remote', 'steplist'):
            local_steps.append(step)

    for step in local_steps:
        #setting step to active
        tool = chip.get('flowgraph', step, 'tool')
        searchdir = "siliconcompiler.tools." + tool
        modulename = '.'+tool+'_setup'
        chip.logger.info(f"Setting up tool '{tool}' for remote '{step}' step")

        #Loading all tool modules and checking for errors
        module = importlib.import_module(modulename, package=searchdir)
        setup_tool = getattr(module, "setup_tool")
        setup_tool(chip, step, str(0))

        # Run the actual import step locally.
        manager = multiprocessing.Manager()
        error = manager.dict()
        active = manager.dict()
        chip._runstep(step, str(0), active, error)

    # Set 'steplist' to only the remote steps, for the future server-side run.
    remote_steplist = []
    for step in chip.getkeys('flowgraph'):
        if not step in local_steps:
            remote_steplist.append(step)
    chip.set('steplist', remote_steplist, clobber=True)

    # Upload the results of the local import stage.
    # Zip the 'import' directory.
    local_build_dir = stepdir = '/'.join([chip.get('dir'),
                                          chip.get('design'),
                                          f"{chip.get('jobname')}0"])
    subprocess.run(['zip',
                    '-r',
                    'import.zip',
                    '.'],
                   cwd=local_build_dir)

    # Upload the archive to the 'import/' server endpoint.
    upload_import_dir(chip)

###################################
def client_decrypt(chip):
    '''Helper method to decrypt project data before running a job on it.
    '''

    root_dir = chip.get('dir')
    job_nameid = f"{chip.get('jobname')}0"

    # Create cipher for decryption.
    with open(chip.get('remote', 'key'), 'r') as keyin:
        dk = keyin.read().encode()
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
                    '%s/%s/%s'%(root_dir, chip.get('design'), job_nameid)])
    subprocess.run(['unzip',
                    '-o',
                    '%s/%s.zip'%(root_dir, job_nameid)],
                   cwd='%s/%s/%s'%(root_dir, chip.get('design'), job_nameid))

###################################
def client_encrypt(chip):
    '''Helper method to re-encrypt project data after processing.
    '''

    root_dir = chip.get('dir')
    job_nameid = f"{chip.get('jobname')}0"

    # Create cipher for decryption.
    with open(chip.get('remote', 'key'), 'r') as keyin:
        dk = keyin.read().encode()
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
                    '%s.zip'%job_nameid,
                    '.'],
                   cwd='%s/%s/%s'%(root_dir, chip.get('design'), job_nameid))

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
        with open('%s/%s/%s/%s.zip'%(root_dir, chip.get('design'), job_nameid, job_nameid), 'rb') as rf:
            while True:
                chunk = rf.read(1024)
                if not chunk:
                    break
                wf.write(encryptor.update(chunk))
        # Write out any remaining data; CTR mode does not require padding.
        wf.write(encryptor.finalize())

    # Delete decrypted data.
    shutil.rmtree('%s/%s/%s'%(root_dir, chip.get('design'), job_nameid))
    os.remove('%s/%s.zip'%(root_dir, job_nameid))

###################################
def remote_run(chip):
    '''Helper method to run a job stage on a remote compute cluster.
    Note that files will not be copied to the remote stage; typically
    the source files will be copied into the cluster's storage before
    calling this method.
    If the "-remote" parameter was not passed in, this method
    will print a warning and do nothing.
    This method assumes that the given stage should not be skipped,
    because it is called from within the `Chip.run(...)` method.

    '''

    # Time how long the process has been running for.
    step_start = time.monotonic()

    # Ask the remote server to start processing the requested step.
    request_remote_run(chip)

    # Check the job's progress periodically until it finishes.
    is_busy = True
    while is_busy:
      chip.logger.info("Job is still running. (%d seconds)"%(
                       int(time.monotonic() - step_start)))
      time.sleep(3)
      try:
          is_busy = is_job_busy(chip)
      except:
          # Sometimes an exception is raised if the request library cannot
          # reach the server due to a transient network issue.
          # Retrying ensures that jobs don't break off when the connection drops.
          is_busy = True
          chip.logger.info("Unknown network error encountered: retrying.")
    chip.logger.info("Remote job run completed!")

###################################
def request_remote_run(chip):
    '''Helper method to make a web request to start a job stage.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/remote_run/'

    # Use authentication if necessary.
    post_params = {'chip_cfg': chip.cfg}
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        # Read the key and encode it in base64 format.
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['params'] = {
            'username': chip.get('remote', 'user'),
            'key': b64_key,
            'job_hash': chip.get('remote', 'jobhash'),
        }
    else:
        post_params['params'] = {
            'job_hash': chip.get('remote', 'jobhash'),
        }

    # Make the actual request.
    # Redirected POST requests are translated to GETs. This is actually
    # part of the HTTP spec, so we need to manually follow the trail.
    redirect_url = remote_run_url
    while redirect_url:
        resp = requests.post(redirect_url,
                             data=json.dumps(post_params),
                             allow_redirects=False)
        if resp.status_code == 302:
            redirect_url = resp.headers['Location']
        else:
            chip.logger.info(resp.text)
            return

###################################
def is_job_busy(chip):
    '''Helper method to make an async request asking the remote server
    whether a job is busy, or ready to accept a new step.
    Returns True if the job is busy, False if not.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/check_progress/'

    # Set common parameters.
    post_params = {
        'job_hash': chip.get('remote', 'jobhash'),
        'job_id': chip.get('jobid'),
    }

    # Set authentication parameters if necessary.
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['username'] = chip.get('remote', 'user')
        post_params['key'] = b64_key

    # Make the request and print its response.
    redirect_url = remote_run_url
    while redirect_url:
        resp = requests.post(redirect_url,
                             data=json.dumps(post_params),
                             allow_redirects=False)
        if resp.status_code == 302:
            redirect_url = resp.headers['Location']
        else:
            return (resp.text != "Job has no running steps.")

###################################
def delete_job(chip):
    '''Helper method to delete a job from shared remote storage.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/delete_job/'

    # Set common parameter.
    post_params = {
        'job_hash': chip.get('remote', 'jobhash'),
    }

    # Set authentication parameters if necessary.
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['username'] = chip.get('remote', 'user')
        post_params['key'] = b64_key

    # Make the request.
    redirect_url = remote_run_url
    while redirect_url:
        resp = requests.post(redirect_url,
                             data=json.dumps(post_params),
                             allow_redirects=False)
        if resp.status_code == 302:
                redirect_url = resp.headers['Location']
        else:
            response = resp.text
            return response

###################################
def upload_import_dir(chip):
    '''Helper method to make an async request uploading the post-import
    files to the remote compute cluster.
    '''

    # Set the request URL.
    remote_run_url = get_base_url(chip) + '/import/'

    # Set common parameters.
    post_params = {
        'job_hash': chip.get('remote', 'jobhash'),
        'job_name': chip.get('jobname'),
    }

    # Set authentication parameters and encrypt data if necessary.
    # TODO-review: Should an error be thrown if only 'user' or 'key' is present?
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
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
        with open('%s.pub'%os.path.abspath(chip.get('remote', 'key')), 'r') as f:
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
        local_build_dir = stepdir = '/'.join([chip.get('dir'),
                                              chip.get('design'),
                                              f"{chip.get('jobname')}0"])
        with open(local_build_dir + '/import.crypt', 'wb') as wf:
            with open(local_build_dir + '/import.zip', 'rb') as rf:
                while True:
                    chunk = rf.read(1024)
                    if not chunk:
                        break
                    wf.write(encryptor.update(chunk))
            # Write out any remaining data; CTR mode does not require padding.
            wf.write(encryptor.finalize())

        # Set up encryption and authentication parameters in the request body.
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params['username'] = chip.get('remote', 'user')
        post_params['key'] = b64_key
        post_params['aes_key'] = base64.urlsafe_b64encode(aes_key_enc).decode()
        post_params['aes_iv'] = base64.urlsafe_b64encode(aes_iv).decode()

        # Set up 'temporary cloud host' parameters.
        num_temp_hosts = int(chip.get('remote', 'hosts'))
        if num_temp_hosts > 0:
            post_params['new_hosts'] = num_temp_hosts
            if len(chip.get('remote', 'ram')) > 0:
                post_params['new_host_ram'] = int(chip.get('remote', 'ram'))
            if len(chip.get('remote', 'threads')) > 0:
                post_params['new_host_threads'] = int(chip.get('remote', 'threads'))

        # Upload the encrypted file.
        upload_file = os.path.abspath(local_build_dir + '/import.crypt')

    # (If '-remote_user' and '-remote_key' are not both specified:)
    else:
        # No authorizaion configured; upload the unencrypted archive.
        import_loc = '/'.join([chip.get('dir'),
                               chip.get('design'),
                               f"{chip.get('jobname')}0",
                               'import.zip'])
        upload_file = os.path.abspath(import_loc)

    # Make the 'import' API call and print the response.
    redirect_url = remote_run_url
    while redirect_url:
        with open(upload_file, 'rb') as f:
            resp = requests.post(redirect_url,
                                 files={'import': f,
                                        'params': json.dumps(post_params)},
                                 allow_redirects=False)
            if resp.status_code == 302:
                redirect_url = resp.headers['Location']
            elif resp.status_code >= 400:
                chip.logger.info(resp.text)
                chip.logger.error('Error importing project data; quitting.')
                sys.exit(1)
            else:
                chip.logger.info(resp.text)
                return

###################################
def fetch_results_request(chip):
    '''Helper method to fetch job results from a remote compute cluster.
    '''

    # Set the request URL.
    job_hash = chip.get('remote', 'jobhash')
    remote_run_url = get_base_url(chip) + '/get_results/' + job_hash + '.zip'

    # Set authentication parameters if necessary.
    if (('user' in chip.getkeys('remote') and chip.get('remote', 'user')) and \
        ('key' in chip.getkeys('remote') and chip.get('remote', 'key'))):
        with open(os.path.abspath(chip.get('remote', 'key')), 'rb') as f:
            key = f.read()
        b64_key = base64.urlsafe_b64encode(key).decode()
        post_params = {
            'username': chip.get('remote', 'user'),
            'key': b64_key,
        }
    else:
        post_params = {}

    # Make the web request, and stream the results archive in chunks.
    redirect_url = remote_run_url
    can_redirect = False
    while redirect_url:
        with open('%s.zip'%job_hash, 'wb') as zipf:
            resp = requests.post(redirect_url,
                                 data=json.dumps(post_params),
                                 allow_redirects=can_redirect,
                                 stream=True)
            if resp.status_code == 302:
                redirect_url = resp.headers['Location']
            elif resp.status_code == 303:
                redirect_url = resp.headers['Location']
                can_redirect = True
            else:
                shutil.copyfileobj(resp.raw, zipf)
                return

###################################
def fetch_results(chip):
    '''Helper method to fetch and open job results from a remote compute cluster.
    '''

    # Fetch the remote archive after the export stage.
    fetch_results_request(chip)

    # Unzip the results.
    top_design = chip.get('design')
    job_hash = chip.get('remote', 'jobhash')
    subprocess.run(['unzip', '%s.zip'%job_hash])
    # Remove the results archive after it is extracted.
    os.remove('%s.zip'%job_hash)

    # Call 'delete_job' to remove the run from the server.
    delete_job(chip)

    # For encrypted jobs each permutation's result is encrypted in its own archive.
    # For unencrypted jobs, results are simply stored in the archive.
    if ('key' in chip.getkeys('remote')) and chip.get('remote', 'key'):
        # Decrypt the block cipher key using the user's private key.
        with open('%s/import.bin'%job_hash, 'rb') as f:
            aes_key_enc = f.read()
        with open('%s'%os.path.abspath(chip.get('remote', 'key')), 'r') as f:
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

        # Decrypt the results using the original initialization vector.
        # Read in the iv.
        job_nameid = f"{chip.get('jobname')}0"
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
        perm_dir = '%s/%s'%(top_design, job_nameid)
        subprocess.run(['mkdir', '-p', perm_dir], cwd=job_hash)
        subprocess.run(['unzip', '-d', perm_dir, '%s.zip'%job_nameid], cwd=job_hash)

    # Remove dangling 'import' symlinks if necessary.
    for import_link in glob.iglob(job_hash + '/' + top_design + '/**/import0',
                                  recursive=True):
        if os.path.islink(import_link):
            os.remove(import_link)
    # Copy the results into the local build directory, and remove the
    # unzipped directory (including encrypted archives).
    local_dir = chip.get('dir')
    shutil.copytree(job_hash + '/' + top_design,
                    local_dir + '/' + top_design,
                    dirs_exist_ok = True)
    shutil.rmtree(job_hash)

    # Ensure that QT will open a GUI window.
    os.environ['QT_QPA_PLATFORM'] = ''
    # Find a list of GDS files to open.
    klayout_cmd = []
    for gds_file in glob.iglob(f'{os.path.abspath(local_dir)}/{top_design}/**/*.[gG][dD][sS]',
                               recursive=True):
        klayout_cmd.append(gds_file)

    # Done; display the results using klayout.
    # TODO: Raise an exception or print an error message if no GDS files exist?
    if klayout_cmd:
        klayout_cmd.insert(0, 'klayout')
        subprocess.run(klayout_cmd)
