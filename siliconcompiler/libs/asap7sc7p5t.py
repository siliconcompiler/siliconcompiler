import os
import siliconcompiler

def make_docs():
    '''
    ASAP 7 7.5-track standard cell library.
    '''

    chip = siliconcompiler.Chip()
    setup(chip)
    return chip

def setup(chip):

    foundry = 'virtual'
    process = 'asap7'
    libtype = '7p5t'
    rev = 'r1p7'
    corner = 'typical'
    objectives = ['setup']

    all_libs = {
        'asap7sc7p5t_rvt' : 'R',
        'asap7sc7p5t_lvt' : 'L',
        'asap7sc7p5t_slvt' : 'SL'
    }

    for libname in all_libs.keys():
        libdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'libs', libname, rev)
        suffix = all_libs[libname]

        # rev
        chip.set('library',libname, 'package', 'version',rev)

        chip.set('library', libname, 'pdk', 'asap7')

        # timing
        chip.add('library', libname, 'nldm', corner, 'lib',
                 libdir+'/nldm/'+libname+'_ff.lib')

        # lef
        chip.add('library',libname,'lef',
                 libdir+'/lef/'+libname+'.lef')
        # gds
        chip.add('library',libname,'gds',
                 libdir+'/gds/'+libname+'.gds')

        # site name
        chip.set('library', libname, 'site', 'asap7sc7p5t', 'symmetry', 'Y')
        chip.set('library', libname, 'site', 'asap7sc7p5t', 'size', (0.054,0.270))

        # lib arch
        chip.set('library',libname,'arch',libtype)

        #default input driver
        chip.add('library',libname,'cells', 'driver', f"BUFx2_ASAP7_75t_{suffix}")

        # clock buffers
        chip.add('library',libname,'cells','clkbuf', f"BUFx2_ASAP7_75t_{suffix}")

        # tie cells
        chip.add('library',libname,'cells','tie', [f"TIEHIx1_ASAP7_75t_{suffix}/H",
                                                   f"TIELOx1_ASAP7_75t_{suffix}/L"])

        # buffer
        # TODO: Need to fix this syntax!, not needed by modern tools!
        chip.add('library',libname,'cells','buf', [f"BUFx2_ASAP7_75t_{suffix}/A/Y"])

        # hold cells
        chip.add('library',libname,'cells','hold', f"BUFx2_ASAP7_75t_{suffix}")

        # filler
        chip.add('library',libname,'cells','filler', [f"FILLER_ASAP7_75t_{suffix}"])

        # Stupid small cells
        chip.add('library',libname,'cells','ignore', ["*x1_ASAP7*",
                                                      "*x1p*_ASAP7*",
                                                      "*xp*_ASAP7*",
                                                      "SDF*",
                                                      "ICG*",
                                                      "DFFH*"])

        # Tapcell
        chip.add('library',libname,'cells','tapcell', f"TAPCELL_ASAP7_75t_{suffix}")

        # Endcap
        chip.add('library',libname,'cells','endcap', f"DECAPx1_ASAP7_75t_{suffix}")
