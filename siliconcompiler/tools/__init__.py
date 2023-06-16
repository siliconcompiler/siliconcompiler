from enum import Flag, auto


class SkipCheck(Flag):
    '''
    Enum class to indicate which checks need to be skipped.
    '''

    exe_empty = auto()

    version_return_code = auto()
