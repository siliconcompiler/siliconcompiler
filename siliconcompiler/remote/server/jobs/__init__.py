'''
The job: creating one, feeding it bytes, running it, and saying what it did.

**submit checks the digest against what storage reports and answers `202`;
only then, while staging, is the archive extracted, the manifest read and every
check re-run against what the read returned.** Getting that order wrong is how
an archive bomb gets opened. Reorder nothing here without reading this again.

**No manifest is parsed in this process** (contract §1): the read runs in a
process of its own (`manifestread`), and only its data summary is acted on.

One module per step of a job's life, composed into
:class:`~siliconcompiler.remote.server.jobs.service.JobService`:

``create``          the create body, reuse, and what is asked for at create
``continuations``   a run that starts part-way through its flow
``submit``          the upload grant, the submit, and the archive's checks
``staging``         the manifest's read, fetching, sending a job back
``pythonenv``       a job's Python packages, installed while it stages
``dispatching``     handing a staged job to the scheduler
``lifecycle``       list, get, cancel, delete, archive
``reconcile``       what the run says, written into the store
``results``         artifacts and logs, as a caller reaches them
``rows``            ownership, state moves, and the job object
``common``          constants, small helpers and exceptions they share
'''

from siliconcompiler.remote.server.jobs.common import MAX_REASON
from siliconcompiler.remote.server.jobs.service import JobService

__all__ = ["JobService", "MAX_REASON"]
