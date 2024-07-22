class NodeStatus():
    # Could use Python 'enum' class here, but that doesn't work nicely with
    # schema.
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'
    SKIPPED = 'skipped'


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
