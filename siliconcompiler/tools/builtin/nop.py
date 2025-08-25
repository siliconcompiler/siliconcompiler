from siliconcompiler.tools.builtin import BuiltinTask


class NOPTask(BuiltinTask):
    '''
    A no-operation that passes inputs to outputs.
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "nop"
