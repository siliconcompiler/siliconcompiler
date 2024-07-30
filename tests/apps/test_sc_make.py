import pytest

from siliconcompiler.apps import sc_make


@pytest.mark.parametrize('target', ('asic', 'lint'))
def test_sc_make(target, monkeypatch, capfd, datadir):
    '''Test sc-make'''

    monkeypatch.setattr('sys.argv', [
        'sc-make', '-C', datadir, target])
    assert sc_make.main() == 0
    assert f"{target.upper()} MAKE" in capfd.readouterr().out


def test_sc_make_default(monkeypatch, capfd, datadir):
    '''Test sc-make'''

    monkeypatch.setattr('sys.argv', [
        'sc-make', '-C', datadir])
    assert sc_make.main() == 0
    assert "LINT MAKE" in capfd.readouterr().out


@pytest.mark.parametrize('target', ('target0', 'target1'))
def test_sc_make_with_argument(target, monkeypatch, capfd, datadir):
    '''Test sc-make'''

    monkeypatch.setattr('sys.argv', [
        'sc-make', '-C', datadir, 'has_arg', '--target', target])
    assert sc_make.main() == 0
    assert f"target {target}" in capfd.readouterr().out


@pytest.mark.parametrize('target', ('target0', 'target1'))
def test_sc_make_with_argument2(target, monkeypatch, capfd, datadir):
    '''Test sc-make'''

    monkeypatch.setattr('sys.argv', [
        'sc-make', '-C', datadir, 'has_arg2', '--target', target, '--count', '5'])
    assert sc_make.main() == 0
    assert f"target {target} 5" in capfd.readouterr().out


def test_sc_make_help(monkeypatch, capfd, datadir):
    '''Test sc-make'''

    monkeypatch.setattr('sys.argv', ['sc-make', '-C', datadir, '-h'])
    with pytest.raises(SystemExit):
        assert sc_make.main() == 0
    output = capfd.readouterr()
    assert "LOOK FOR THIS TEXT IN HELP" in output.out
    assert "lint" in output.out
    assert "asic" in output.out
    assert "LINT HELP" in output.out


def test_sc_make_file(monkeypatch, capfd, datadir):
    '''Test sc-make with -f'''

    monkeypatch.setattr('sys.argv', [
        'sc-make', '-C', datadir, '-f', 'make_other.py', 'asic'])
    assert sc_make.main() == 0
    assert "ASIC OTHER" in capfd.readouterr().out


def test_sc_make_file_with_import(monkeypatch, capfd, datadir):
    '''Test sc-make with -f'''

    monkeypatch.setattr('sys.argv', [
        'sc-make', '-C', datadir, '-f', 'make_with_import.py', 'asic_here'])
    assert sc_make.main() == 0
    output = capfd.readouterr()
    assert "ASIC MAKE" in output.out
    assert "ASIC IMPORT" in output.out
