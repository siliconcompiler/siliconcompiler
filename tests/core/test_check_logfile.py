import os
import siliconcompiler
import logging
import re


def test_check_logfile(datadir, caplog):

    chip = siliconcompiler.Chip('gcd')
    chip.logger = logging.getLogger()
    chip.load_target('freepdk45_demo')

    # add regex
    chip.add('tool', 'openroad', 'task', 'place', 'regex', 'errors', "ERROR",
             step='place', index='0')
    chip.add('tool', 'openroad', 'task', 'place', 'regex', 'warnings', "WARNING",
             step='place', index='0')
    chip.add('tool', 'openroad', 'task', 'place', 'regex', 'warnings', "-v DPL",
             step='place', index='0')

    # check log
    logfile = os.path.join(datadir, 'place.log')
    chip.check_logfile(step='place', logfile=logfile)

    # check line numbers in log and file
    warning_with_line_number = ' 89: [WARNING GRT-0043] No OR_DEFAULT vias defined.'
    assert warning_with_line_number in caplog.text
    # newline insures warnings are printed first, errors second
    warning_error_number = 'Number of warnings: 1\n.*Number of errors: 0'
    assert re.search(warning_error_number, caplog.text)
    warnings_file = 'place.warnings'
    assert os.path.isfile(warnings_file)
    with open(warnings_file) as file:
        assert warning_with_line_number in file.read()


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_check_logfile(datadir(__file__))
