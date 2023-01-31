
class SiliconCompilerError(Exception):
    ''' Minimal Exception wrapper used to raise sc runtime errors.
    '''
    def __init__(self, message):
        super().__init__(message)
