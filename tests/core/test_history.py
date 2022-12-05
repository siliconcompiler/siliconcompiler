import os
import siliconcompiler

def test_history(datadir):

    chip = siliconcompiler.Chip('gcd')

    # mandatory to have manifest loaded
    manifest = os.path.join(datadir, 'gcd.pkg.json')
    chip.read_manifest(manifest)

    # record history
    chip.schema.record_history()

    # record new manifest
    chip.write_manifest("history.json")

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_history(datadir(__file__))
