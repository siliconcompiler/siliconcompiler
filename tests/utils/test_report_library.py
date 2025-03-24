import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('target', [
    'asap7_demo',
    'skywater130_demo',
    'gf180_demo',
    'ihp130_demo',
    'freepdk45_demo'
])
def test_report(target, scroot, monkeypatch):
    monkeypatch.syspath_prepend(scroot)

    from scripts import report_library

    monkeypatch.setattr('sys.argv', ['report', '-target', target])

    assert report_library.main() == 0


def test_report_no_target(scroot, monkeypatch):
    monkeypatch.syspath_prepend(scroot)

    from scripts import report_library

    monkeypatch.setattr('sys.argv', ['report'])

    with pytest.raises(ValueError, match='-target is required'):
        report_library.main()
