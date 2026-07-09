from siliconcompiler.tools.sby import SBYTask


class ProveTask(SBYTask):
    '''
    Unbounded proof (k-induction): prove that the assertions in the
    design hold for all reachable states. The induction length is
    configured with the depth var.
    '''

    def task(self):
        return "prove"
