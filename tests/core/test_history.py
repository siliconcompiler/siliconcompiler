import siliconcompiler
from siliconcompiler.targets import freepdk45_demo


def test_history(datadir):

    chip = siliconcompiler.Chip('gcd')
    chip.load_target(freepdk45_demo)

    # Set values in manifest
    chip.set('metric', 'utilization', 10, step='floorplan', index='0')

    # record history
    chip.schema.record_history()

    assert chip.get('history', 'job0', 'metric', 'utilization', step='floorplan', index='0') == 10

    # record new manifest
    chip.write_manifest("history.json")


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_history(datadir(__file__))
