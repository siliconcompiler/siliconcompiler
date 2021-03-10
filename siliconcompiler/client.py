# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import aiohttp
import asyncio
import os
import subprocess
import time

###################################
def remote_run(chip, stage):
    '''Helper method to run a job stage on a remote compute cluster.
    Note that files will not be copied to the remote stage; typically
    the source files will be copied into the cluster's storage before
    calling this method.
    If the "-remote" parameter was not passed in, this method
    will print a warning and do nothing.

    '''

    #Looking up stage numbers
    stages = (chip.cfg['compile_steps']['value'] +
              chip.cfg['dv_steps']['value'])
    current = stages.index(stage)
    laststage = stages[current-1]
    start = stages.index(chip.cfg['start']['value'][-1]) #scalar
    stop = stages.index(chip.cfg['stop']['value'][-1]) #scalar
    #Check if stage should be explicitly skipped
    skip = stage in chip.cfg['skip']['value']

    if stage not in stages:
        chip.logger.error('Illegal stage name %s', stage)
        return
    elif (current < start) | (current > stop):
        chip.logger.info('Skipping stage: %s', stage)
        return
    else:
        chip.logger.info('Running stage: %s', stage)

    # Run the import stage locally, and upload sources to shared storage.
    if stage == 'import':
        chip.run(stage)
        upload_sources_to_cluster(chip)
        return

    # Ask the remote server to start processing the requested step.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(request_remote_run(chip, stage))

    # Check the job's progress periodically until it finishes.
    is_busy = True
    while is_busy:
      print("%s stage running. Please wait."%stage)
      time.sleep(1)
      is_busy = loop.run_until_complete(is_job_busy(chip, stage))
    print("%s stage completed!"%stage)

###################################
async def request_remote_run(chip, stage):
    '''Helper method to make an async request to start a job stage.

    '''
    async with aiohttp.ClientSession() as session:
        async with session.post("http://%s:%s/remote_run/%s/%s"%(
                                    chip.cfg['remote']['value'][0],
                                    chip.cfg['remoteport']['value'][0],
                                    chip.status['job_hash'],
                                    stage),
                                json=chip.cfg) \
        as resp:
            print(await resp.text())

###################################
async def is_job_busy(chip, stage):
    '''Helper method to make an async request asking the remote server
    whether a job is busy, or ready to accept a new step.
    Returns True if the job is busy, False if not.

    '''

    async with aiohttp.ClientSession() as session:
        async with session.get("http://%s:%s/check_progress/%s/%s"%(
                               chip.cfg['remote']['value'][0],
                               chip.cfg['remoteport']['value'][0],
                               chip.status['job_hash'],
                               stage)) \
        as resp:
            response = await resp.text()
            return (response != "Job has no running steps.")

###################################
async def upload_import_dir(chip):
    '''Helper method to make an async request uploading the post-import
    files to the remote compute cluster.
    '''

    async with aiohttp.ClientSession() as session:
        with open('%s/import.zip'%(chip.cfg['build']['value'][0]), 'rb') as f:
            async with session.post("http://%s:%s/import/%s"%(
                                        chip.cfg['remote']['value'][0],
                                        chip.cfg['remoteport']['value'][0],
                                        chip.status['job_hash']),
                                    data={'import': f}) \
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
    subprocess.run(['zip',
                    '-r',
                    'import.zip',
                    'import'],
                    cwd=chip.cfg['build']['value'][0])

    # Upload the archive to the 'import' server endpoint.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(upload_import_dir(chip))
