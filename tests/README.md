# SiliconCompiler tests

This directory contains tests for SiliconCompiler. These tests are written using
the pytest framework. This README documents how our tests are organized and
describes some of our project-specific practices and standards for writing
tests.

## Running tests

Running `pytest` in the SC root directory will by default discover and run all
tests under `tests/`.

To select specific tests, you can pass in paths to specific directories or
files, for example:

- `pytest tests/core`: runs all core tests
- `pytest tests/flows/test_asicflow.py`: runs any tests in test_asicflow.py
- `pytest tests/core/test_target.py::test_target_valid`: run individual
  `test_target_valid` test among the multiple defined in `test_target.py`

In addition, some tests are annotated with pytest "markers", which specify
specific properties (in our case, generally how often and what machines are used
to run them within our CI system). You can select tests using the `-m` flag and
providing generic Python-style boolean expressions based on these markers. For
example:

- `pytest -m eda`: runs all tests with "eda" marker
- `pytest -m "not quick"`: runs all tests without the "quick" marker

### Running all tests run by CI on push

Run `pytest -m "not eda or quick"`.

### Debugging tests

By default, pytest will swallow test output (unless it fails), and run each test
in a unique temporary directory. This can make it tough to get insight into
what a test is doing.

Some of our test files end in a block
```python
if __name__ == '__main__':
  ...
```
that calls a test function directly in order to easily run and debug tests
directly using Python. This works around these pytest features.

#### Running through pytest

For tests without the above boilerplate, you can  approximate the default Python
behavior while executing a test with `pytest`. Use the `-s` flag to disable
output capture, and use the custom `--cwd` flag to run it from the current
working directory. For example, to run the OpenROAD test:

`pytest -s --cwd tests/tools/test_openroad.py`

To select a single test in a file, you can use `::` and specify the name of the test:

`pytest -s --cwd tests/tools/test_yosys.py::test_yosys_lec`

You can also use the `-k` flag to select the test without specifying a filename
(note this will select partial matches as well, so `-k test_yosys_lec` will
select `test_yosys_lec` and `test_yosys_lec_broken`):

`pytest -s --cwd -k test_openroad`

## Writing tests

### Directory contents and structure

#### `conftest.py`

This file contains the definitions of our custom fixtures as well as
additional pytest configuration.

#### `fixtures.py`

All of the non-"autouse" fixtures defined in conftest.py have a pure Python
implementation in this file. This allows us to implement a pattern where we can
run individual tests directly from the Python interpreter (without going through
pytest).

You can do so by adding a block that only runs if the current module is a main
module, calling the pure Python fixture function in this block, and then passing
the result to the test function you want to directly call. For example, to run a
test `test_foo` that depends on `myfixture`, you'd add the following to
`test_foo.py`:

```python
if __name__ == '__main__':
    from tests.fixtures import myfixture
    test_foo(myfixture())
```

All of these fixture implementations take no arguments except `datadir`, which
takes in the full path to the current test file (so you should always pass in
`__file__`).

#### `data/`

This directory contains common data used by tests across multiple test
directories. To access files in this directory, we suggest making a test depend
on the `scroot` fixture, then building the directory path like so:

```python
datadir = os.path.join(scroot, 'tests', 'data')
```

This may change in the future if we add a dedicated fixture for accessing this
directory.

#### Test directories

The remaining directories all contain test files. Use the following rules to
decide where a test should go:

- `flow/`: tests that exercise some SC flow, whether it be ASIC, FPGA, DV, or
  custom.
- `tools/`: tests that exercise a single tool through SC.
  - These are simple unit tests that check installation and basic functionality
  - One file per tool
  - A test file can have multiple tests
  - Name of file should be `test_<name-of-tool>`.py
  - Use existing data files if possible
  - All tests must at a minimum check that output file was produced
- `designs/`: tests that run a flow specifically to check support for a
  particular design.

All Python API unit tests should go in a directory corresponding to the relevant
Python module. So far we have `core/`, `crypto/`, `floorplan/`, and `leflib/`.

Each of these directories can contain a `data/` directory which holds data files
specific to those tests in particular. To access this directory, make your test
depend on the `datadir` fixture, which provides an absolute path to this directory.

### Custom Fixtures

To view our globally available custom fixtures, run `pytest --fixtures tests/conftest.py`.

### Markers

We've defined the following markers:

- `@pytest.mark.quick`: always run this test on push, even if it requires EDA tools.
- `@pytest.mark.eda`: this test requires EDA tools installed to run. By default these tests will be run nightly, not on push.

To view documentation for these and builtin markers, run `pytest --markers`.
