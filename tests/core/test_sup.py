import siliconcompiler
import shutil
import os

def test_sup():
    ''' SUP basic test
    '''

    registry = 'test_registry'

    if os.path.exists(registry):
       shutil.rmtree(registry)

    chip = siliconcompiler.Chip(design='top')
    chip.set('registry',registry)

    # 1. Create a set of dummy chips and save to disk
    for i in ('a', 'b', 'c'):
        os.makedirs(f"{registry}/{i}")
        ver1 = '0.0.0'
        chip.set('package', 'dependency', i, ver1)
        l1 = siliconcompiler.Chip(design=i)
        for j in ('0', '1', '2'):
            dep2 = i+j
            ver2 = f"0.0.{j}"
            os.makedirs(f"{registry}/{dep2}")
            l1.add('package', 'dependency', dep2, ver2)
            l2 = siliconcompiler.Chip(design=dep2)
            l2.write_manifest(f"{registry}/{dep2}/{dep2}-{ver2}.json")
        l1.write_manifest(f"{registry}/{i}/{i}-{ver1}.json")

    # 3. Resolve dependencies and write dependency graph
    chip.update_depgraph()
    chip.write_depgraph('top.png')

#########################
if __name__ == "__main__":
    test_sup()
