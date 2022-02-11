import os
import siliconcompiler

def make_docs():
    '''
    Nangate open standard cell library for FreePDK45.
    '''

    chip = siliconcompiler.Chip()
    setup(chip)
    return chip

def setup(chip):

    libname = 'nangate45'
    foundry = 'virtual'
    process = 'freepdk45'
    libtype = '10t'
    rev = 'r1p0'
    corner = 'typical'
    objectives = ['setup']

    libdir = os.path.join('..',
                          'third_party',
                          'pdks',
                          foundry,
                          process,
                          'libs',
                          libname,
                          rev)

    # standard cell typ
    chip.set('library',libname,'type','stdcell')

    # rev
    chip.set('library',libname, 'package', 'version',rev)

    chip.set('library', libname, 'pdk', 'freepdk45')

    # timing
    chip.add('library',libname, 'nldm', corner, 'lib',
             libdir+'/lib/NangateOpenCellLibrary_typical.lib')

    # lef
    chip.add('library',libname,'lef',
             libdir+'/lef/NangateOpenCellLibrary.macro.mod.lef')
    # gds
    chip.add('library',libname,'gds',
             libdir+'/gds/NangateOpenCellLibrary.gds')
    # site name
    chip.set('library',libname,
             'site','FreePDK45_38x28_10R_NP_162NW_34O',
             'symmetry', 'Y')
    chip.set('library',libname,
             'site','FreePDK45_38x28_10R_NP_162NW_34O',
             'size', (0.19,1.4))

    # lib arch
    chip.set('library',libname,'arch',libtype)

    # driver
    chip.add('library',libname, 'cells','driver', "BUF_X4")

    # clock buffers
    chip.add('library',libname,'cells','clkbuf', "BUF_X4")

    # tie cells
    chip.add('library',libname,'cells','tie', ["LOGIC1_X1/Z",
                                               "LOGIC0_X1/Z"])

    # buffer cell
    chip.add('library', libname,'cells', 'buf', ['BUF_X1/A/Z'])

    # hold cells
    chip.add('library',libname,'cells','hold', "BUF_X1")

    # filler
    chip.add('library',libname,'cells','filler', ["FILLCELL_X1",
                                                  "FILLCELL_X2",
                                                  "FILLCELL_X4",
                                                  "FILLCELL_X8",
                                                  "FILLCELL_X16",
                                                  "FILLCELL_X32"])

    # Stupid small cells
    chip.add('library',libname,'cells','ignore', ["AOI211_X1",
                                                  "OAI211_X1"])

    # Tapcell
    chip.add('library',libname,'cells','tapcell', "FILLCELL_X1")

    # Endcap
    chip.add('library',libname,'cells','endcap', "FILLCELL_X1")

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest('nangate45.json')
