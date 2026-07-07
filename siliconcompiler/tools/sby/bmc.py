from siliconcompiler.tools.sby import SBYTask


class BMCTask(SBYTask):
    '''
    Bounded model check: prove that no assertion in the design can be
    violated within the configured number of cycles (var: depth).
    '''

    def task(self):
        return "bmc"
