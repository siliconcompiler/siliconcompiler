import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('target', [
    'asap7_demo',
    'skywater130_demo',
    'gf180_demo'
])
def test_report(target, scroot, monkeypatch):
    monkeypatch.syspath_prepend(scroot)

    from scripts import report_library

    monkeypatch.setattr('sys.argv', ['report', '-target', target])

    assert report_library.main() == 0
