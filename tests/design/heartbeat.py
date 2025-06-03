from siliconcompiler.design import DesignSchema

class Heartbeat(DesignSchema):

    def __init__(self, name='heartbeat'):

        DesignSchema.__init__(self, name='heartbeat')

        # files
        source = ['heartbeat.v']
        sdc = ['heartbeat.sdc']
        tb =  ['tb.v']

        # rtl
        self.add_file(fileset='rtl', files=source)
        self.option(fileset='rtl', topmodule='heartbeat')

        # constraints
        self.add_file(fileset='constraint', files=sdc)

        # tb
        self.add_file(fileset='testbench', files=tb)
        self.option(fileset='testbench', topmodule='tb')

#d = Heartbeat()
