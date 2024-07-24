import siliconcompiler
from siliconcompiler import Schema

import os
import pytest
import shutil
from pathlib import Path


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
                 step='place', index='0')

    gcd_chip.set('option', 'to', 'cts')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None
    assert gcd_chip.find_result('def', step='cts') is None

    # Fix place step and re-run
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.40',
                 step='place', index='0')
    gcd_chip.run()

    # Ensure floorplan did not get re-run
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) == old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is not None
    assert gcd_chip.find_result('def', step='cts') is not None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_changed_value(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.20',
                 step='place', index='0')

    gcd_chip.set('option', 'to', 'cts')

    gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)
    pl_result = gcd_chip.find_result('def', step='place')
    assert pl_result is not None
    old_pl_mtime = os.path.getmtime(pl_result)

    assert gcd_chip.find_result('def', step='cts') is not None

    # Fix place step and re-run
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.40',
                 step='place', index='0')
    gcd_chip.run()

    # Ensure floorplan did not get re-run
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) == old_fp_mtime

    pl_result = gcd_chip.find_result('def', step='place')
    assert pl_result is not None
    assert os.path.getmtime(pl_result) != old_pl_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is not None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_changed_file_no_hash_no_changes(gcd_chip):
    gcd_chip.set('option', 'to', 'floorplan')

    gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    old_im_result = os.path.getmtime(im_result)
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None

    gcd_chip.run()

    # Ensure import did not re-run
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    assert os.path.getmtime(im_result) == old_im_result

    # Ensure floorplan did not re-run
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) == old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_changed_file_no_hash_timestamp(gcd_chip):
    gcd_chip.set('option', 'to', 'floorplan')

    shutil.copyfile(
        gcd_chip.find_files('input', 'constraint', 'sdc',
                            step=Schema.GLOBAL_KEY, index=Schema.GLOBAL_KEY)[0],
        './gcd.sdc')

    gcd_chip.set('input', 'constraint', 'sdc', './gcd.sdc')

    gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    old_im_result = os.path.getmtime(im_result)
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None

    # Change the timestamp on SDC file
    Path('./gcd.sdc').touch()
    gcd_chip.run()

    # Ensure import did not re-run
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    assert os.path.getmtime(im_result) == old_im_result

    # Ensure floorplan re-ran
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) != old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_changed_file_no_hash_dir_timestamp(gcd_chip):
    gcd_chip.set('option', 'to', 'syn')

    os.makedirs('ydirs', exist_ok=True)
    with open('ydirs/test.v', 'w') as f:
        f.write('\n')

    gcd_chip.add('option', 'ydir', 'ydirs')

    shutil.copyfile(
        gcd_chip.find_files('input', 'constraint', 'sdc',
                            step=Schema.GLOBAL_KEY, index=Schema.GLOBAL_KEY)[0],
        './gcd.sdc')

    gcd_chip.set('input', 'constraint', 'sdc', './gcd.sdc')

    gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    old_im_result = os.path.getmtime(im_result)
    syn_result = gcd_chip.find_result('vg', step='syn')
    assert syn_result is not None
    old_syn_mtime = os.path.getmtime(syn_result)

    assert gcd_chip.find_result('def', step='floorplan') is None

    # Change the timestamp on SDC file
    Path('ydirs/test.v').touch()
    gcd_chip.run()

    # Ensure import re-ran
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    assert os.path.getmtime(im_result) != old_im_result

    # Ensure floorplan re-ran
    syn_result = gcd_chip.find_result('vg', step='syn')
    assert syn_result is not None
    assert os.path.getmtime(syn_result) != old_syn_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='floorplan') is None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_changed_file_no_hash_value_change(gcd_chip):
    gcd_chip.set('option', 'to', 'floorplan')

    # Copy file before to ensure timestamps are consistent
    shutil.copyfile(
        gcd_chip.find_files('input', 'constraint', 'sdc',
                            step=Schema.GLOBAL_KEY, index=Schema.GLOBAL_KEY)[0],
        './gcd.sdc')

    gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    old_im_result = os.path.getmtime(im_result)
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None

    # Change the value of SDC
    gcd_chip.set('input', 'constraint', 'sdc', './gcd.sdc')

    gcd_chip.run()

    # Ensure import did not re-run
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    assert os.path.getmtime(im_result) == old_im_result

    # Ensure floorplan re-ran
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) != old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_changed_file_with_hash(gcd_chip):
    gcd_chip.set('option', 'to', 'floorplan')
    gcd_chip.set('option', 'hash', True)

    gcd_chip.run()

    # Store last modified time of floorplan
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    old_im_result = os.path.getmtime(im_result)
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None

    # File moved, but no changes
    shutil.copyfile(gcd_chip.find_files('input', 'rtl', 'verilog',
                                        step='import_verilog', index=0)[0],
                    './gcd.v')
    gcd_chip.set('input', 'rtl', 'verilog', './gcd.v')
    gcd_chip.run()

    # Ensure nothing re-ran
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    assert os.path.getmtime(im_result) == old_im_result

    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) == old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume_changed_file_with_hash_file_modify(gcd_chip):
    gcd_chip.set('option', 'to', 'floorplan')
    gcd_chip.set('option', 'hash', True)

    gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    old_im_result = os.path.getmtime(im_result)
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None

    # File moved, and modified
    shutil.copyfile(gcd_chip.find_files('input', 'rtl', 'verilog',
                                        step='import_verilog', index=0)[0],
                    './gcd.v')
    with open('./gcd.v', 'a') as f:
        f.write('\n\n\n')
    gcd_chip.set('input', 'rtl', 'verilog', './gcd.v')
    gcd_chip.run()

    # Ensure import re-ran
    im_result = gcd_chip.find_result('v', step='import_verilog')
    assert im_result is not None
    assert os.path.getmtime(im_result) != old_im_result

    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) != old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is None
