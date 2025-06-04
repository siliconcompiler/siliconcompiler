from siliconcompiler.design import DesignSchema

from increment import Increment

class Heartbeat(DesignSchema):

    def __init__(self):

        super().__init__('heartbeat')

        # files
        source = ['data/heartbeat.v']
        sdc = ['data/heartbeat.sdc']
        tb =  ['data/tb.v']

        # rtl
        self.fileset='rtl'
        self.topmodule='heartbeat'
        self.add_file(source)

        # constraints
        self.fileset='constraint'
        self.add_file(sdc)

        # tb
        self.fileset='testbench'
        self.topmodule='tb'
        self.add_file(tb)

        # dependencie
        self.use(Increment())

#self.package_root()
#self.package_home(path='git+https://github.com/acme')
#d = Heartbeat()

#self.use(Heartbeat())<--!!!!
#self.use(Heartbeat)
