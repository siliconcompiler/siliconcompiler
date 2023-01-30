
class SiliconCompilerError(Exception):
    ''' Minimal Exception wrapper used to raise sc runtime errors.
    '''
    def __init__(self, message):
        super(Exception, self).__init__(message)
