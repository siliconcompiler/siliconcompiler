# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler.schema import *

class Library:
    """Siliconcompiler Compiler Chip Object Class"""

    def __init__(self):
        '''Initializes Library Object
        '''

        #Schema defined in separate file
        self.lib = schema_lib()
        
        pass
    
    ################################
    # Verilog Source Input
    ################################

    def read_verilog(self, cell, filename):
        '''Reads in verilog macro used to setup a cell  
        '''
        pass

    def read_vcd(self, cell, filename):
        '''Reads in VCD stimulus for characterization
        '''
        pass

    ################################
    # Cell Access Functions
    ################################

    def get(self, *args):
        '''Gets a library property
        '''
        pass

    def set(self, *args):
        '''Gets a library property
        '''
        pass
    
    ################################
    # Characterization
    ################################

    def write_testbench(self, cell, filename, sim='xyce'):
        '''Writes out the complete testbench for a cell
        '''
        pass

    def analyze(self, cell, dirname, sim='xyce'):
        '''Analyzes results from simulation
        '''
        pass

    ################################
    # Write out Library
    ################################
    
    def write_verilog(self, filename):
        '''Writes out library verilog file
        '''
        pass

    def write_timing(self, filename):
        '''Writes out library timing file (.lib, .ccs)
        '''
        pass
      
    def write_lef(self, filename):
        '''Writes out library LEF file
        '''
        pass

    def write_netlist(self, filename):
        '''Write out library netlist  
        '''
        pass

################################
# Run-time basic test
################################    
if __name__ == '__main__':
    lib = Library()




    

    
