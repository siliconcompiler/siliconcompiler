# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os
import tarfile
import pytest
import glob


@pytest.fixture(scope='module')
def chip(oh_dir, tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp('archive_run')
    os.chdir(tmpdir)

    srcdir = os.path.join(oh_dir, 'stdlib', 'hdl')

    chip = siliconcompiler.Chip('oh_parity')
    chip.input(os.path.join(srcdir, 'oh_parity.v'))
    chip.set('option', 'steplist', ['import', 'syn'])
    chip.load_target('freepdk45_demo')
    chip.run()

    return chip


@pytest.mark.eda
@pytest.mark.quick
def test_archive(chip):
    chip.archive()

    assert os.path.isfile('oh_parity_job0.tgz')

    with tarfile.open('oh_parity_job0.tgz', 'r:gz') as f:
        contents = f.getnames()

    for item in ('build/oh_parity/job0/oh_parity.pkg.json',
                 'build/oh_parity/job0/import/0/reports',
                 'build/oh_parity/job0/import/0/outputs',
                 'build/oh_parity/job0/import/0/import.log',
                 'build/oh_parity/job0/syn/0/reports',
                 'build/oh_parity/job0/syn/0/outputs',
                 'build/oh_parity/job0/syn/0/syn.log'):
        assert item in contents


@pytest.mark.eda
@pytest.mark.quick
def test_archive_step_index(chip):
    chip.archive(step='import', index='0')

    assert os.path.isfile('oh_parity_job0_import0.tgz')

    with tarfile.open('oh_parity_job0_import0.tgz', 'r:gz') as f:
        contents = f.getnames()

    for item in ('build/oh_parity/job0/oh_parity.pkg.json',
                 'build/oh_parity/job0/import/0/reports',
                 'build/oh_parity/job0/import/0/outputs',
                 'build/oh_parity/job0/import/0/import.log'):
        assert item in contents

    for item in contents:
        assert not item.startswith('build/oh_parity/job0/syn')


@pytest.mark.eda
@pytest.mark.quick
def test_archive_all(chip):
    chip.archive(include='*', archive_name='all.tgz')

    assert os.path.isfile('all.tgz')

    with tarfile.open('all.tgz', 'r:gz') as f:
        contents = f.getnames()

    for item in glob.glob('build/oh_parity/job0/**'):
        assert item in contents


@pytest.mark.eda
@pytest.mark.quick
def test_archive_include(chip):
    chip.archive(include=['*.log', 'reports/*', 'outputs/*.pkg.json'])

    assert os.path.isfile('oh_parity_job0.tgz')

    with tarfile.open('oh_parity_job0.tgz', 'r:gz') as f:
        contents = f.getnames()

    for item in ('build/oh_parity/job0/oh_parity.pkg.json',
                 'build/oh_parity/job0/import/0/import.log',
                 'build/oh_parity/job0/import/0/outputs/oh_parity.pkg.json',
                 'build/oh_parity/job0/syn/0/syn.log',
                 'build/oh_parity/job0/syn/0/reports/stat.json',
                 'build/oh_parity/job0/syn/0/outputs/oh_parity.pkg.json'):
        assert item in contents

    for item in contents:
        if not item.endswith('oh_parity.pkg.json'):
            assert 'outputs/' not in item
