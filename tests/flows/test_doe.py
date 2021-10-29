import siliconcompiler
import multiprocessing
import os
import pytest

# unit routine
def run_design(datadir, design, N, job):

    chip = siliconcompiler.Chip(loglevel='INFO')
    chip.set('design', design)
    chip.add('source', os.path.join(datadir, f'{design}.v'))
    chip.set('param', 'N', str(N))
    chip.set('jobname', job)
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('steplist', ['import', 'syn'])
    chip.target("asicflow_freepdk45")
    chip.run()

@pytest.mark.eda
@pytest.mark.quick
def test_doe(scroot):
    '''Test running multiple experiments sweeping different parameters in
    parallel using multiprocessing library.'''

    datadir = os.path.join(scroot, 'third_party', 'designs', 'oh', 'stdlib', 'hdl')
    design = 'oh_add'
    N = [4, 8, 16, 32, 64, 128]

    # Define parallel processingg
    processes = []
    for i in range(len(N)):
        job = 'job' + str(i)
        processes.append(multiprocessing.Process(target=run_design,
                                                args=(datadir,
                                                      design,
                                                      str(N[i]),
                                                      job
                                                )))

    # Boiler plate start and join
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    # Post-processing data
    chip = siliconcompiler.Chip()
    prev_area = 0
    for i in range(len(N)):
        jobname = 'job'+str(i)
        chip.read_manifest(f"build/{design}/{jobname}/syn/0/outputs/{design}.pkg.json", job=jobname)
        area = chip.get('metric','syn','0','cellarea','real', job=jobname)

        # expect to have increasing area as we increase adder width
        assert area > prev_area
        prev_area = area
