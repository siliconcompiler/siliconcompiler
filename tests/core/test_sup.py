import siliconcompiler as sc
from siliconcompiler.package import Sup
import pytest
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
        l1 = sc.Chip(i)
        l1.load_target('freepdk45_demo')
        l1.set('package', 'version', '0.0.0')
        l1.set('package', 'license', 'MIT')
        l1.set('package', 'description', 'sup?')
        for j in ('0', '1', '2'):
            dep2 = i+j
            os.makedirs(f"{builddir}/{dep2}/job0/export/outputs", exist_ok=True)
            l1.add('package', 'dependency', dep2, f"0.0.{j}")
            l2 = sc.Chip(dep2)
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
    chip = sc.Chip('top')
    chip.load_target('freepdk45_demo')
    chip.set('option', 'registry', registry)
    chip.set('package', 'version', f"0.0.0")
    chip.set('package', 'license', 'MIT')
    chip.set('package', 'description', 'sup?')
    for i in ('a', 'b', 'c'):
        chip.set('package', 'dependency', i, '0.0.0')
    chip.set('option', 'autoinstall', True)
    chip.update()

    # 4. Dump updated manifest and depgraph
    chip.write_manifest('top.tcl')
    #chip.write_depgraph('tree.png')

#########################
def test_sup_circ_import():
    ''' Test that SUP detects circular imports, and throws an error without freezing.
    '''

    registry = 'test_registry'
    builddir = 'test_build'
    cachedir = 'test_cache'
    os.environ['SC_HOME'] = cachedir
    os.makedirs(f"{cachedir}/.sc/registry", exist_ok=True)

    # Create two packages, 'A' and 'B'.
    packs = {}
    for i in ('A', 'B'):
        os.makedirs(f"{builddir}/{i}/job0/export/outputs", exist_ok=True)
        p = sc.Chip(design=i)
        p.load_target('freepdk45_demo')
        p.set('package', 'version', '0.0.0')
        p.set('package', 'license', 'MIT')
        p.set('package', 'description', f'sup {i}?')
        packs[i] = p

    # Create a circular dependency link, and save the manifests.
    packs['A'].add('package', 'dependency', 'B', '0.0.0')
    packs['B'].add('package', 'dependency', 'A', '0.0.0')
    packs['A'].write_manifest(f"{builddir}/A/job0/export/outputs/A.pkg.json")
    packs['B'].write_manifest(f"{builddir}/B/job0/export/outputs/B.pkg.json")

    # Package each dependency with SUP.
    for i in ('A', 'B'):
        pp = sc.package.Sup()
        pp.publish(f"{builddir}/{i}/job0/export/outputs/{i}.pkg.json", registry)

    # Attempt to build a design with each circular dependency, verify errors are thrown.
    for i in ('A', 'B'):
        chip = sc.Chip(design='top')
        chip.load_target('freepdk45_demo')
        chip.set('option', 'registry', registry)
        chip.set('package', 'version', f"0.0.0")
        chip.set('package', 'license', 'MIT')
        chip.set('package', 'description', 'sup?')
        chip.set('package', 'dependency', i, '0.0.0')
        chip.set('option', 'autoinstall', True)
        with pytest.raises(sc.SiliconCompilerError) as pytest_wrapped_e:
            chip.update()

#########################
if __name__ == "__main__":
    test_sup()
