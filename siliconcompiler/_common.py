class NodeStatus():
    # node waiting to run
    PENDING = 'pending'

    # node ready to run and waiting
    QUEUED = 'queued'

    # node running
    RUNNING = 'running'

    # node exit status
    SUCCESS = 'success'
    ERROR = 'error'
    SKIPPED = 'skipped'
    TIMEOUT = 'timeout'

    def is_done(status):
        return status in (
            NodeStatus.SUCCESS,
            NodeStatus.ERROR,
            NodeStatus.SKIPPED,
            NodeStatus.TIMEOUT
        )

    def is_running(status):
        return status in (
            NodeStatus.QUEUED,
            NodeStatus.RUNNING
        )

    def is_waiting(status):
        return status in (
            NodeStatus.PENDING,
        )


###############################################################################
# Package Customization classes
###############################################################################
class SiliconCompilerError(Exception):
    ''' Minimal Exception wrapper used to raise sc runtime errors.
    '''
    def __init__(self, message, chip=None):
        super(Exception, self).__init__(message)

        if chip:
            logger = getattr(chip, 'logger', None)
            if logger:
                logger.error(message)
