import pathlib
import pytest
import os
import tempfile

import os.path

from pathlib import Path

from siliconcompiler import Design
from siliconcompiler.schema_support.filesetschema import FileSetSchema
from siliconcompiler.schema import NamedSchema


@pytest.fixture
def design_with_tmpdir():
    """Provide a Design with temporary working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            design = Design()
            yield design
        finally:
            os.chdir(orig_cwd)


@pytest.fixture
def temp_files(design_with_tmpdir):
    """Create temporary test files."""
    files = {}
    for name in ['test.v', 'test2.v', 'test.sv', 'test.sdc', 'test.lef', 'test.def']:
        Path(name).write_text(f'// {name}')
        files[name] = name
    return files


# ============================================================================
# Basic Initialization and Structure Tests
# ============================================================================

# Initialization

def test_filesetschema_instantiation():
    """Test basic FileSetSchema creation."""
    schema = FileSetSchema()
    assert schema is not None
    assert isinstance(schema, FileSetSchema)


def test_filesetschema_getdict_type():
    """Test _getdict_type returns correct type."""
    schema = FileSetSchema()
    assert schema._getdict_type() == 'FileSetSchema'


def test_filesetschema_has_expected_methods():
    """Test FileSetSchema has all expected public methods."""
    schema = FileSetSchema()
    expected_methods = [
        'add_file', 'get_file', 'has_file',
        'set_topmodule', 'get_topmodule',
        'add_idir', 'get_idir', 'has_idir',
        'add_define', 'get_define',
        'add_undefine', 'get_undefine',
        'add_libdir', 'get_libdir', 'has_libdir',
        'add_lib', 'get_lib',
        'set_param', 'get_param',
        'add_depfileset', 'get_depfileset'
    ]
    for method in expected_methods:
        assert hasattr(schema, method), f"FileSetSchema missing method {method}"


# ============================================================================
# Tests for set_topmodule() and get_topmodule()
# ============================================================================

# Topmodule

def test_set_topmodule_valid_identifier(design_with_tmpdir):
    """Test setting topmodule with valid Verilog identifier."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        result = d.set_topmodule('mytop')
        assert d.get_topmodule() == 'mytop'


def test_set_topmodule_with_leading_underscore(design_with_tmpdir):
    """Test topmodule starting with underscore is valid."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_topmodule('_module')
        assert d.get_topmodule() == '_module'


def test_set_topmodule_with_numbers(design_with_tmpdir):
    """Test topmodule with embedded numbers."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_topmodule('top123module')
        assert d.get_topmodule() == 'top123module'


def test_set_topmodule_with_multiple_underscores(design_with_tmpdir):
    """Test topmodule with multiple underscores."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_topmodule('top_module_name')
        assert d.get_topmodule() == 'top_module_name'


def test_set_topmodule_none_raises_error(design_with_tmpdir):
    """Test setting None raises ValueError."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"^set_topmodule cannot process None$"):
            d.set_topmodule(None)


def test_set_topmodule_non_string_raises_error(design_with_tmpdir):
    """Test setting non-string raises ValueError."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"topmodule must be a string"):
            d.set_topmodule(123)


def test_set_topmodule_leading_digit_invalid(design_with_tmpdir):
    """Test topmodule starting with digit is invalid."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"is not a legal topmodule string"):
            d.set_topmodule('1_invalid')


def test_set_topmodule_with_hyphen_invalid(design_with_tmpdir):
    """Test topmodule with hyphen is invalid."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"is not a legal topmodule string"):
            d.set_topmodule('top-module')


def test_set_topmodule_with_space_invalid(design_with_tmpdir):
    """Test topmodule with space is invalid."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"is not a legal topmodule string"):
            d.set_topmodule('top module')


def test_set_topmodule_with_special_char_invalid(design_with_tmpdir):
    """Test topmodule with special character is invalid."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"is not a legal topmodule string"):
            d.set_topmodule('top$module')


def test_set_topmodule_empty_string_invalid(design_with_tmpdir):
    """Test topmodule with empty string is invalid."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"is not a legal topmodule string"):
            d.set_topmodule('')


def test_set_topmodule_multiple_times(design_with_tmpdir):
    """Test setting topmodule multiple times overwrites."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_topmodule('first')
        assert d.get_topmodule() == 'first'
        d.set_topmodule('second')
        assert d.get_topmodule() == 'second'


# ============================================================================
# Tests for add_define() and get_define()
# ============================================================================

# Define

def test_add_define_simple(design_with_tmpdir):
    """Test adding a simple define."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_define('MACRO')
        defines = d.get_define()
        assert 'MACRO' in defines


def test_add_define_with_value(design_with_tmpdir):
    """Test adding a define with value."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_define('WIDTH=32')
        defines = d.get_define()
        assert any('WIDTH' in str(d) for d in defines)


def test_add_define_multiple_sequential(design_with_tmpdir):
    """Test adding multiple defines sequentially."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_define('MACRO1')
        d.add_define('MACRO2')
        d.add_define('MACRO3')
        defines = d.get_define()
        assert 'MACRO1' in defines
        assert 'MACRO2' in defines
        assert 'MACRO3' in defines


def test_add_define_with_clobber(design_with_tmpdir):
    """Test adding define with clobber clears previous."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_define('MACRO1')
        d.add_define('MACRO2')
        initial_len = len(d.get_define())
        d.add_define('MACRO3', clobber=True)
        defines = d.get_define()
        assert defines == ['MACRO3']


def test_add_define_none_raises_error(design_with_tmpdir):
    """Test adding None as define raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.add_define(None)


def test_get_define_returns_list(design_with_tmpdir):
    """Test get_define returns a list."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_define('MACRO')
        result = d.get_define()
        assert isinstance(result, list)


# ============================================================================
# Tests for add_undefine() and get_undefine()
# ============================================================================

# Undefine

def test_add_undefine_single(design_with_tmpdir):
    """Test adding single undefine."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_undefine('MACRO')
        undefines = d.get_undefine()
        assert 'MACRO' in undefines


def test_add_undefine_multiple(design_with_tmpdir):
    """Test adding multiple undefines."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_undefine('MACRO1')
        d.add_undefine('MACRO2')
        undefines = d.get_undefine()
        assert 'MACRO1' in undefines
        assert 'MACRO2' in undefines


def test_add_undefine_with_clobber(design_with_tmpdir):
    """Test adding undefine with clobber."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_undefine('MACRO1')
        d.add_undefine('MACRO2')
        d.add_undefine('MACRO3', clobber=True)
        undefines = d.get_undefine()
        assert undefines == ['MACRO3']


def test_add_undefine_none_raises_error(design_with_tmpdir):
    """Test adding None as undefine raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.add_undefine(None)


def test_get_undefine_returns_list(design_with_tmpdir):
    """Test get_undefine returns list."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_undefine('MACRO')
        result = d.get_undefine()
        assert isinstance(result, list)


# ============================================================================
# Tests for add_idir() / get_idir() / has_idir()
# ============================================================================

# Idir

def test_add_idir_single_path(design_with_tmpdir):
    """Test adding single include directory."""
    d = design_with_tmpdir
    # Create actual directory for path validation
    Path('includes1').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_idir('includes1')
        idirs = d.get_idir()
        assert len(idirs) > 0


def test_add_idir_multiple(design_with_tmpdir):
    """Test adding multiple include directories."""
    d = design_with_tmpdir
    Path('/tmp/includes1').mkdir(exist_ok=True)
    Path('/tmp/includes2').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_idir('/tmp/includes1')
        d.add_idir('/tmp/includes2')
        idirs = [str(i) for i in d.get_idir()]
        assert any('/tmp/includes1' in str(i) for i in idirs)
        assert any('/tmp/includes2' in str(i) for i in idirs)


def test_add_idir_with_clobber(design_with_tmpdir):
    """Test adding idir with clobber."""
    d = design_with_tmpdir
    Path('inc1').mkdir(exist_ok=True)
    Path('inc2').mkdir(exist_ok=True)
    Path('inc3').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_idir('inc1')
        d.add_idir('inc2')
        d.add_idir('inc3', clobber=True)
        idirs = d.get_idir()
        assert len(idirs) == 1


def test_add_idir_none_raises_error(design_with_tmpdir):
    """Test adding None as idir raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.add_idir(None)


def test_get_idir_returns_list(design_with_tmpdir):
    """Test get_idir returns list."""
    d = design_with_tmpdir
    Path('includes_test').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_idir('includes_test')
        result = d.get_idir()
        assert isinstance(result, list)


def test_has_idir_when_empty(design_with_tmpdir):
    """Test has_idir returns False when empty."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        assert not d.has_idir()


def test_has_idir_when_present(design_with_tmpdir):
    """Test has_idir returns True when present."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_idir('/path/to/includes')
        assert d.has_idir()


# ============================================================================
# Tests for add_libdir() / get_libdir() / has_libdir()
# ============================================================================

# Libdir

def test_add_libdir_single_path(design_with_tmpdir):
    """Test adding single library directory."""
    d = design_with_tmpdir
    Path('libs1').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_libdir('libs1')
        libdirs = d.get_libdir()
        assert len(libdirs) > 0


def test_add_libdir_multiple(design_with_tmpdir):
    """Test adding multiple library directories."""
    d = design_with_tmpdir
    Path('lib1').mkdir(exist_ok=True)
    Path('lib2').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_libdir('lib1')
        d.add_libdir('lib2')
        libdirs = d.get_libdir()
        assert len(libdirs) >= 2


def test_add_libdir_with_clobber(design_with_tmpdir):
    """Test adding libdir with clobber."""
    d = design_with_tmpdir
    Path('lib_a').mkdir(exist_ok=True)
    Path('lib_b').mkdir(exist_ok=True)
    Path('lib_c').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_libdir('lib_a')
        d.add_libdir('lib_b')
        d.add_libdir('lib_c', clobber=True)
        libdirs = d.get_libdir()
        assert len(libdirs) == 1


def test_add_libdir_none_raises_error(design_with_tmpdir):
    """Test adding None as libdir raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.add_libdir(None)


def test_get_libdir_returns_list(design_with_tmpdir):
    """Test get_libdir returns list."""
    d = design_with_tmpdir
    Path('libs_test').mkdir(exist_ok=True)
    with d.active_fileset('rtl'):
        d.add_libdir('libs_test')
        result = d.get_libdir()
        assert isinstance(result, list)


def test_has_libdir_when_empty(design_with_tmpdir):
    """Test has_libdir returns False when empty."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        assert not d.has_libdir()


def test_has_libdir_when_present(design_with_tmpdir):
    """Test has_libdir returns True when present."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_libdir('/path/to/libs')
        assert d.has_libdir()


# ============================================================================
# Tests for add_lib() / get_lib()
# ============================================================================

# Lib

def test_add_lib_single(design_with_tmpdir):
    """Test adding single library."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_lib('mylib')
        libs = d.get_lib()
        assert 'mylib' in libs


def test_add_lib_multiple(design_with_tmpdir):
    """Test adding multiple libraries."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_lib('lib1')
        d.add_lib('lib2')
        d.add_lib('lib3')
        libs = d.get_lib()
        assert 'lib1' in libs
        assert 'lib2' in libs
        assert 'lib3' in libs


def test_add_lib_with_clobber(design_with_tmpdir):
    """Test adding lib with clobber."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_lib('lib1')
        d.add_lib('lib2')
        d.add_lib('lib3', clobber=True)
        libs = d.get_lib()
        assert libs == ['lib3']


def test_add_lib_none_raises_error(design_with_tmpdir):
    """Test adding None as lib raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.add_lib(None)


def test_get_lib_returns_list(design_with_tmpdir):
    """Test get_lib returns list."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_lib('mylib')
        result = d.get_lib()
        assert isinstance(result, list)


# ============================================================================
# Tests for set_param() / get_param()
# ============================================================================

# Param

def test_set_param_simple(design_with_tmpdir):
    """Test setting simple parameter."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_param('WIDTH', '32')
        assert d.get_param('WIDTH') == '32'


def test_set_param_multiple(design_with_tmpdir):
    """Test setting multiple parameters."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_param('PARAM1', 'value1')
        d.set_param('PARAM2', 'value2')
        d.set_param('PARAM3', 'value3')
        assert d.get_param('PARAM1') == 'value1'
        assert d.get_param('PARAM2') == 'value2'
        assert d.get_param('PARAM3') == 'value3'


def test_set_param_overwrite(design_with_tmpdir):
    """Test setting parameter multiple times overwrites."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_param('PARAM', 'value1')
        assert d.get_param('PARAM') == 'value1'
        d.set_param('PARAM', 'value2')
        assert d.get_param('PARAM') == 'value2'


def test_set_param_none_name_raises_error(design_with_tmpdir):
    """Test setting None as parameter name raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.set_param(None, 'value')


def test_set_param_non_string_value_raises_error(design_with_tmpdir):
    """Test setting non-string value raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.set_param('PARAM', 123)


def test_set_param_none_value_raises_error(design_with_tmpdir):
    """Test setting None as value raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError):
            d.set_param('PARAM', None)


def test_set_param_with_special_chars(design_with_tmpdir):
    """Test setting parameter with special characters in value."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.set_param('PATH', '/path/to/file.txt')
        assert d.get_param('PATH') == '/path/to/file.txt'


# ============================================================================
# Tests for add_depfileset() / get_depfileset()
# ============================================================================

# Depfileset

def test_get_depfileset_returns_list(design_with_tmpdir):
    """Test get_depfileset returns list."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        result = d.get_depfileset()
        assert isinstance(result, list)


def test_get_depfileset_empty_initially(design_with_tmpdir):
    """Test get_depfileset is empty initially."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        result = d.get_depfileset()
        assert result == []


# ============================================================================
# Tests for get_file() / has_file()
# ============================================================================

# FileOperations

def test_get_file_empty(design_with_tmpdir):
    """Test get_file on empty fileset."""
    d = design_with_tmpdir
    result = d.get_file('rtl')
    assert result == []


def test_get_file_with_filetype_string(design_with_tmpdir, temp_files):
    """Test get_file with filetype as string."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
    result = d.get_file('rtl', filetype='verilog')
    assert len(result) > 0
    assert any('test.v' in str(f) for f in result)


def test_get_file_with_filetype_list(design_with_tmpdir, temp_files):
    """Test get_file with filetype as list."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
    result = d.get_file('rtl', filetype=['verilog', 'systemverilog'])
    assert len(result) > 0


def test_has_file_empty_fileset(design_with_tmpdir):
    """Test has_file on empty fileset."""
    d = design_with_tmpdir
    assert not d.has_file('rtl')


def test_has_file_with_filetype(design_with_tmpdir, temp_files):
    """Test has_file with filetype specified."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
    assert d.has_file('rtl', filetype='verilog')


def test_has_file_with_filetype_list(design_with_tmpdir, temp_files):
    """Test has_file with filetype as list."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
    assert d.has_file('rtl', filetype=['verilog', 'systemverilog'])


def test_has_file_with_nonexistent_filetype(design_with_tmpdir, temp_files):
    """Test has_file returns False for non-existent filetype."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
    assert not d.has_file('rtl', filetype='systemverilog')


# ============================================================================
# Tests for add_file()
# ============================================================================

# AddFile

def test_add_file_string(design_with_tmpdir, temp_files):
    """Test adding file as string."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        result = d.add_file('test.v', filetype='verilog')
        assert result is not None


def test_add_file_path_object(design_with_tmpdir, temp_files):
    """Test adding file as Path object."""
    d = design_with_tmpdir
    filepath = Path('test.v')
    with d.active_fileset('rtl'):
        result = d.add_file(filepath, filetype='verilog')
        assert result is not None


def test_add_file_list(design_with_tmpdir, temp_files):
    """Test adding multiple files as list."""
    d = design_with_tmpdir
    files = ['test.v', 'test2.v']
    with d.active_fileset('rtl'):
        result = d.add_file(files, filetype='verilog')
        assert result is not None


def test_add_file_tuple(design_with_tmpdir, temp_files):
    """Test adding files as tuple."""
    d = design_with_tmpdir
    files = ('test.v', 'test2.v')
    with d.active_fileset('rtl'):
        result = d.add_file(files, filetype='verilog')
        assert result is not None


def test_add_file_set(design_with_tmpdir, temp_files):
    """Test adding files as set."""
    d = design_with_tmpdir
    files = {'test.v', 'test2.v'}
    with d.active_fileset('rtl'):
        result = d.add_file(files, filetype='verilog')
        assert result is not None


def test_add_file_none_raises_error(design_with_tmpdir):
    """Test adding None raises error."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        with pytest.raises(ValueError, match=r"^add_file cannot process None$"):
            d.add_file(None)


def test_add_file_with_clobber(design_with_tmpdir, temp_files):
    """Test add_file with clobber clears previous."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
        d.add_file('test2.v', filetype='verilog')
        d.add_file('test.v', filetype='verilog', clobber=True)
        files = d.get_file('rtl', filetype='verilog')
        assert len(files) == 1


def test_add_file_empty_list(design_with_tmpdir):
    """Test adding empty list."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        result = d.add_file([], filetype='verilog')
        assert result is not None or result == []


def test_add_file_infers_filetype(design_with_tmpdir, temp_files):
    """Test add_file infers filetype from extension."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v')
        files = d.get_file('rtl')
        assert len(files) > 0


def test_add_file_multiple_filesets(design_with_tmpdir, temp_files):
    """Test adding files to different filesets."""
    d = design_with_tmpdir
    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
    with d.active_fileset('sim'):
        d.add_file('test.sv', filetype='systemverilog')
    rtl_files = d.get_file('rtl')
    sim_files = d.get_file('sim')
    assert len(rtl_files) > 0
    assert len(sim_files) > 0


# ============================================================================
# Tests for _generate_doc() - implementation requires complex doc parameter
# ============================================================================

# DocGeneration

def test_generate_doc_exists():
    """Test that _generate_doc method exists."""
    schema = FileSetSchema()
    assert hasattr(schema, '_generate_doc')
    assert callable(schema._generate_doc)


# ============================================================================
# Integration Tests
# ============================================================================

# Integration

def test_complete_workflow(design_with_tmpdir, temp_files):
    """Test a complete workflow using multiple methods."""
    d = design_with_tmpdir

    with d.active_fileset('rtl'):
        d.add_file(['test.v', 'test2.v'], filetype='verilog')
        d.set_topmodule('top_module')
        d.add_define('SIM')
        d.add_idir('/path/to/includes')
        d.set_param('WIDTH', '32')
        d.set_param('DEPTH', '1024')

        # Verify setup
        assert len(d.get_file('rtl', filetype='verilog')) == 2
        assert d.get_topmodule() == 'top_module'
        assert 'SIM' in d.get_define()
        assert d.get_param('WIDTH') == '32'
        assert d.has_idir()


def test_multiple_filesets(design_with_tmpdir, temp_files):
    """Test working with multiple filesets in one design."""
    d = design_with_tmpdir

    with d.active_fileset('rtl'):
        d.add_file('test.v', filetype='verilog')
        d.set_topmodule('rtl_top')

    with d.active_fileset('sim'):
        d.add_file('test.sv', filetype='systemverilog')
        d.set_topmodule('sim_top')

    rtl_files = d.get_file('rtl', filetype='verilog')
    sim_files = d.get_file('sim', filetype='systemverilog')
    assert len(rtl_files) > 0
    assert len(sim_files) > 0

    with d.active_fileset('rtl'):
        assert d.get_topmodule() == 'rtl_top'

    with d.active_fileset('sim'):
        assert d.get_topmodule() == 'sim_top'
