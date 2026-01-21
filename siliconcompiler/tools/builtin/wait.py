from siliconcompiler.tools.builtin import BuiltinTask


class Wait(BuiltinTask):
    '''
    A wait task that stalls the flow until all inputs are available.
    '''
    def __init__(self):
        super().__init__()

    def _set_io_files(self):
        # No file IO needed for wait task
        return

    def task(self):
        return "wait"
