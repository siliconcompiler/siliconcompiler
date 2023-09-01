class NodeStatus():
    # Could use Python 'enum' class here, but that doesn't work nicely with
    # schema.
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'


###############################################################################
# Package Customization classes
###############################################################################
class SiliconCompilerError(Exception):
    ''' Minimal Exception wrapper used to raise sc runtime errors.
    '''
    def __init__(self, message):
        super(Exception, self).__init__(message)
