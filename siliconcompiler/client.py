# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import aiohttp
import asyncio
import os
import subprocess
import time

###################################
def remote_preprocess(chips, cmdlinecfg):
    '''Helper method to perform preprocessing steps for remote cloud jobs,
       if a remote host was configured in the command-line flags.
    '''
    # For remote jobs, run the 'import' stage locally and upload it.
    loop = asyncio.get_event_loop()
    if 'remote' in cmdlinecfg.keys():
        loop.run_until_complete(chips[-1].run(start='import', stop='import'))
        cwd = os.getcwd()
        os.chdir(str(chips[-1].cfg['dir']['value'][-1]) + '/import/job')
        upload_sources_to_cluster(chips[-1])
        os.chdir(cwd)

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
      time.sleep(1)
      is_busy = await is_job_busy(chip, stage)
    print("%s stage completed!"%stage)

    # Increment the stage's jobid value.
    next_id = str(int(chip.cfg['status'][stage]['jobid']['value'][-1])+1)
    chip.cfg['status'][stage]['jobid']['value'] = [next_id]

###################################
async def request_remote_run(chip, stage):
    '''Helper method to make an async request to start a job stage.

    '''
    async with aiohttp.ClientSession() as session:
        async with session.post("http://%s:%s/remote_run/%s/%s"%(
                                    chip.cfg['remote']['value'][-1],
                                    chip.cfg['remoteport']['value'][-1],
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
        async with session.get("http://%s:%s/check_progress/%s/%s/%s"%(
                               chip.cfg['remote']['value'][0],
                               chip.cfg['remoteport']['value'][0],
                               chip.status['job_hash'],
                               stage,
                               chip.cfg['status'][stage]['jobid']['value'][-1])) \
        as resp:
            response = await resp.text()
            return (response != "Job has no running steps.")

###################################
async def delete_job(chip):
    '''Helper method to delete a job from shared remote storage.
    '''

    async with aiohttp.ClientSession() as session:
        async with session.get("http://%s:%s/delete_job/%s"%(
                               chip.cfg['remote']['value'][0],
                               chip.cfg['remoteport']['value'][0],
                               chip.status['job_hash'])) \
        as resp:
            response = await resp.text()
            return response

###################################
async def upload_import_dir(chip):
    '''Helper method to make an async request uploading the post-import
    files to the remote compute cluster.
    '''

    async with aiohttp.ClientSession() as session:
        with open(os.path.abspath('../../import/job/import.zip'), 'rb') as f:
            async with session.post("http://%s:%s/import/%s"%(
                                        chip.cfg['remote']['value'][-1],
                                        chip.cfg['remoteport']['value'][-1],
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
                    '.'])

    # Upload the archive to the 'import' server endpoint.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(upload_import_dir(chip))

def fetch_results(chip):
    '''Helper method to fetch job results from a remote compute cluster.
    '''

    # Fetch the remote archive after the export stage.
    # TODO: Use aiohttp client methods, but wget is simpler for accessing
    # a server endpoint that returns a file object.
    subprocess.run(['wget',
                    "http://%s:%s/get_results/%s.zip"%(
                        chip.cfg['remote']['value'][0],
                        chip.cfg['remoteport']['value'][0],
                        chip.status['job_hash'])])
    # Unzip the result and run klayout to display the GDS file.
    subprocess.run(['unzip', '%s.zip'%chip.status['job_hash']])
    gds_loc = '%s/export/job*/outputs/%s.gds'%(
        chip.status['job_hash'],
        chip.cfg['design']['value'][0],
    )
    subprocess.run(['klayout', gds_loc])
