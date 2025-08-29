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

    @staticmethod
    def is_done(status):
        return status in (
            NodeStatus.SUCCESS,
            NodeStatus.ERROR,
            NodeStatus.SKIPPED,
            NodeStatus.TIMEOUT
        )

    @staticmethod
    def is_running(status):
        return status in (
            NodeStatus.QUEUED,
            NodeStatus.RUNNING
        )

    @staticmethod
    def is_waiting(status):
        return status in (
            NodeStatus.PENDING,
        )

    @staticmethod
    def is_success(status):
        return status in (
            NodeStatus.SUCCESS,
            NodeStatus.SKIPPED
        )

    @staticmethod
    def is_error(status):
        return status in (
            NodeStatus.ERROR,
            NodeStatus.TIMEOUT
        )
