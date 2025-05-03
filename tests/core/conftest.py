import pytest
import pathlib


@pytest.fixture
def cast():
    def _cast(val, sctype):
        if sctype.startswith('['):
            # TODO: doesn't handle examples w/ multiple list items (we do not have
            # currently)
            subtype = sctype.strip('[]')
            return [_cast(val.strip('[]'), subtype)]
        elif sctype.startswith('('):
            vals = val.strip('()').split(',')
            subtypes = sctype.strip('()').split(',')
            return tuple(_cast(v.strip(), subtype.strip()) for v, subtype in zip(vals, subtypes))
        elif sctype == 'float':
            return float(val)
        elif sctype == 'int':
            return int(val)
        elif sctype == 'bool':
            return bool(val)
        elif 'file' in sctype or 'dir' in sctype:
            return pathlib.PureWindowsPath(_cast(val, 'str')).as_posix()
        else:
            # everything else (str) is treated like a string
            return val.strip('"\'')
    return _cast
