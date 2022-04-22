import siliconcompiler as sc
from siliconcompiler.package import Sup
import shutil
import os
import sys

def test_sup():
    ''' SUP basic test
    '''

    registry = 'test_registry'
    builddir = 'test_build'
    cachedir = 'test_cache'
    os.environ['SC_HOME'] = cachedir
    os.makedirs(f"{cachedir}/.sc/registry", exist_ok=True)

    # 1. Create a set of dummy designs with dependencies and save to disk
    for i in ('a', 'b', 'c'):
        os.makedirs(f"{builddir}/{i}/job0/export/outputs", exist_ok=True)
        l1 = sc.Chip(design=i)
        l1.load_target('freepdk45_demo')
        l1.set('package', 'version', '0.0.0')
        l1.set('package', 'license', 'MIT')
        l1.set('package', 'description', 'sup?')
        for j in ('0', '1', '2'):
            dep2 = i+j
            os.makedirs(f"{builddir}/{dep2}/job0/export/outputs", exist_ok=True)
            l1.add('package', 'dependency', dep2, f"0.0.{j}")
            l2 = sc.Chip(design=dep2)
            l2.load_target('freepdk45_demo')
            l2.set('package', 'version', f"0.0.{j}")
            l2.set('package', 'license', 'MIT')
            l2.set('package', 'description', 'sup?')
            l2.write_manifest(f"{builddir}/{dep2}/job0/export/outputs/{dep2}.pkg.json")
        #don't move
        l1.write_manifest(f"{builddir}/{i}/job0/export/outputs/{i}.pkg.json")

    # 2. Package up dependecies using sup
    for i in ('a', 'b', 'c'):
        p = sc.package.Sup()
        p.publish(f"{builddir}/{i}/job0/export/outputs/{i}.pkg.json", registry)
        for j in ('0', '1', '2'):
            dep2 = i+j
            p = sc.package.Sup()
            p.publish(f"{builddir}/{dep2}/job0/export/outputs/{dep2}.pkg.json", registry)

    # 3. Create top object and update dependencies
    chip = sc.Chip(design='top')
    chip.load_target('freepdk45_demo')
    chip.set('registry', registry)
    chip.set('package', 'version', f"0.0.0")
    chip.set('package', 'license', 'MIT')
    chip.set('package', 'description', 'sup?')
    for i in ('a', 'b', 'c'):
        chip.set('package', 'dependency', i, '0.0.0')
    chip.set('autoinstall', True)
    chip.update()

    # 4. Dump updated manifest and depgraph
    chip.write_manifest('top.tcl')
    #chip.write_depgraph('tree.png')

#########################
if __name__ == "__main__":
    test_sup()
