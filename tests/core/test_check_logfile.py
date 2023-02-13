import os
import siliconcompiler

def test_check_logfile(datadir):

    chip = siliconcompiler.Chip('gcd')
    chip.load_target('freepdk45_demo')

    # add regex
    chip.add('tool', 'openroad', 'task', 'place', 'regex', 'warnings', "WARNING", step='place', index='0')
    chip.add('tool', 'openroad', 'task', 'place', 'regex', 'warnings', "-v DPL", step='place', index='0')

    # check log
    logfile = os.path.join(datadir, 'place.log')
    chip.check_logfile(step='place', logfile=logfile)


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_check_logfile(datadir(__file__))
