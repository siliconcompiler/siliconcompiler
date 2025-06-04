from siliconcompiler.design import DesignSchema

class Heartbeat(DesignSchema):

    def __init__(self):

        super().__init__('heartbeat')

        # files
        source = ['heartbeat.v']
        sdc = ['heartbeat.sdc']
        tb =  ['tb.v']

        #self.package_root()
        #self.package_home(path='git+https://github.com/acme')

        #when is this needed? Is there a default?

        # why do path concatenation at source? why not in find files/run?

        # rtl
        self.add_file(fileset='rtl', files=source)
        self.option(fileset='rtl', topmodule='heartbeat')
        self.set('fileset', 'rtl', 'topmodule', 'heartbeat')
        #self.set_libext()
        #self.get_libext()
        #TODO: study some clever APIs?
        # constraints
        self.add_file(fileset='constraint', files=sdc)

        # tb
        self.add_file(fileset='testbench', files=tb)
        self.option(fileset='testbench', topmodule='tb')

#d = Heartbeat()

#self.use(Heartbeat())<--!!!!
#self.use(Heartbeat)
