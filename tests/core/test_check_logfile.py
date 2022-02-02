import os
import siliconcompiler

def test_check_logfile(datadir):

    chip = siliconcompiler.Chip(loglevel="INFO")

    # mandatory to have manifest loaded
    manifest = os.path.join(datadir, 'gcd.pkg.json')
    chip.read_manifest(manifest)

    # add regex
    chip.write_manifest("tmp.json", prune=False)
    chip.add('eda', 'openroad', 'regex', 'place', '0', 'warnings', "WARNING")
    chip.add('eda', 'openroad', 'regex', 'place', '0', 'warnings', "-v DPL")

    # check log
    logfile = os.path.join(datadir, 'place.log')
    chip.check_logfile(step='place', logfile=logfile)


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_check_logfile(datadir(__file__))
