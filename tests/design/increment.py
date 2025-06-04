from siliconcompiler.design import DesignSchema

class Increment(DesignSchema):

    def __init__(self):

        super().__init__('increment')

        # files
        source = ['increment.v']

        # rtl
        self.fileset='rtl'
        self.topmodule='increment'
        self.add_file(source)
