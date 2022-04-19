import siliconcompiler
from siliconcompiler.sup import Sup
import shutil
import os

def test_sup():
    ''' SUP basic test
    '''

    registry = 'test_registry'
    builddir = 'test_build'
    cachedir = 'test_cache'
    os.environ['SC_CACHE'] = cachedir

    # 1. Create a set of dummy designs with dependencies and save to disk
    for i in ('a', 'b', 'c'):
        os.makedirs(f"{builddir}/{i}/job0/export/outputs", exist_ok=True)
        l1 = siliconcompiler.Chip(design=i)
        l1.set('package', 'version', '0.0.0')
        for j in ('0', '1', '2'):
            dep2 = i+j
            os.makedirs(f"{builddir}/{dep2}/job0/export/outputs", exist_ok=True)
            l1.add('package', 'dependency', dep2, f"0.0.{j}")
            l2 = siliconcompiler.Chip(design=dep2)
            l2.set('package', 'version', f"0.0.{j}")
            l2.write_manifest(f"{builddir}/{dep2}/job0/export/outputs/{dep2}.pkg.json")
        l1.write_manifest(f"{builddir}/{i}/job0/export/outputs/{i}.pkg.json")

    # 2. Package up dependecies using sup
    for i in ('a', 'b', 'c'):
        p = Sup()
        p.package(f"{builddir}/{i}/job0/export/outputs/{i}.pkg.json")
        p.publish(registry)
        for j in ('0', '1', '2'):
            dep2 = i+j
            p = Sup()
            p.package(f"{builddir}/{dep2}/job0/export/outputs/{dep2}.pkg.json")
            p.publish(registry)

    # 3. Create top object and update dependencies
    chip = siliconcompiler.Chip(design='top')
    for i in ('a', 'b', 'c'):
        chip.set('package', 'dependency', i, '0.0.0')
    chip.update()
    chip.update_library()

    # 4. Dump updated manifest and depgraph
    chip.write_manifest('top.json')
    chip.write_depgraph('tree.png')

#########################
if __name__ == "__main__":
    test_sup()
