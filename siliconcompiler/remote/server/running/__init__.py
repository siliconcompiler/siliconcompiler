'''
Handing a job to whatever runs it, and the process that runs it.

``dispatch.py``  submitting the run -- a local process or a Slurm batch job -- and
                 polling it
``runner.py``    the process the batch job starts, in the job's own image
``runspec.py``   what the server decides about how a run executes, and the files
                 the run and the API process speak through
'''
