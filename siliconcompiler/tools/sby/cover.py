from siliconcompiler.tools.sby import SBYTask


class CoverTask(SBYTask):
    '''
    Cover check: find, within the configured number of cycles
    (var: depth), a reachable trace for every cover() statement in the
    design.
    '''

    def task(self):
        return "cover"
