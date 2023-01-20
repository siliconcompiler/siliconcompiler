import os
import siliconcompiler

def test_history(datadir):

    chip = siliconcompiler.Chip('gcd')
    chip.load_target('freepdk45_demo')

    # Set values in manifest
    chip.set('metric', 'floorplan', '0', 'utilization', 10)

    # record history
    chip.schema.record_history()

    assert chip.get('history', 'job0', 'metric', 'floorplan', '0', 'utilization') == 10

    # record new manifest
    chip.write_manifest("history.json")

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_history(datadir(__file__))
