import siliconcompiler


def test_get_copy():
    chip = siliconcompiler.Chip('test')
    cfg = chip.get('option', 'cfg')
    cfg.append('manifest.json')
    assert chip.get('option', 'cfg') != cfg
