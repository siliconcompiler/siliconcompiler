import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    sv2v converts SystemVerilog (IEEE 1800-2017) to Verilog
    (IEEE 1364-2005), with an emphasis on supporting synthesizable
    language constructs. The primary goal of this project is to
    create a completely free and open-source tool for converting
    SystemVerilog to Verilog. While methods for performing this
    conversion already exist, they generally either rely on
    commercial tools, or are limited in scope.

    Documentation: https://github.com/zachjs/sv2v

    Sources: https://github.com/zachjs/sv2v

    Installation: https://github.com/zachjs/sv2v

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step', '<step>')
    chip.set('arg','index', '<index>')
    setup(chip)
    return chip


################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    chip.logger.debug("Setting up sv2v")

    tool = 'sv2v'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '--numeric-version')
    chip.set('tool', tool, 'version', '>=0.0.9', clobber=False)
    chip.set('tool', tool, 'threads', step, index,  4, clobber=False)

    # Since we run sv2v after the import/preprocess step, there should be no
    # need for specifying include dirs/defines. However we don't want to pass
    # --skip-preprocessor because there may still be unused preprocessor
    # directives not removed by the importer and passing the --skip-preprocessor
    # flag would cause sv2v to error.

    # since this step should run after import, the top design module should be
    # set and we can read the pickled Verilog without accessing the original
    # sources
    topmodule = chip.top()
    chip.set('tool', tool, 'option', step, index,  [])
    chip.add('tool', tool, 'option', step, index,  "inputs/" + topmodule + ".v")
    chip.add('tool', tool, 'option', step, index,  "--write=outputs/" + topmodule + ".v")

    chip.set('tool', tool, 'input', step, index, f'{topmodule}.v')
    chip.set('tool', tool, 'output', step, index, f'{topmodule}.v')

def parse_version(stdout):
    # 0.0.7-130-g1aa30ea
    return '-'.join(stdout.split('-')[:-1])

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("sv2v.json")
