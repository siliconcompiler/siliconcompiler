import os
import glob
import stat
import sys
import pytest


def test_all_examples_have_test_file(scroot):
    test_folder = os.path.dirname(__file__)
    ex_dir = os.path.join(scroot, 'examples')

    expected_test_files = [
        'conftest.py',
        'test_assert_all_examples.py'
    ]

    for d in os.listdir(ex_dir):
        path = os.path.join(ex_dir, d)
        if os.path.isdir(path):
            expected_test_files.append(f'test_{d}.py')

    # This only holds some files, no runnable example
    expected_test_files.remove("test_fpga_flow.py")

    tests = []
    for f in os.listdir(test_folder):
        path = os.path.join(test_folder, f)
        if os.path.isfile(path):
            tests.append(f)

    for test in tests:
        assert test in expected_test_files, f"Extra test found: {test}"

    for test in expected_test_files:
        assert test in tests, f"Missing test found: {test}"


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='Execution checks do not work on windows.')
def test_all_examples_have_defs(scroot):
    test_folder = os.path.dirname(__file__)
    ex_dir = os.path.join(scroot, 'examples')

    exempt = {
        "picorv32_ram": ["sky130_sram_2k.py"]
    }

    tests = {}
    for d in os.listdir(ex_dir):
        path = os.path.join(ex_dir, d)
        test_path = os.path.join(test_folder, f'test_{d}.py')
        if os.path.isdir(path) and os.path.isfile(test_path):
            tests[path] = test_path

    def check_and_collect_functions(example, ext):
        example_name = os.path.basename(example)

        shell_type = ''
        if ext == 'py':
            shell_type = 'python3'
        if ext == 'sh':
            shell_type = 'bash'

        functions = []
        for shell in glob.glob(os.path.join(example, f"*.{ext}")):
            shell_name = os.path.basename(shell)
            if example_name in exempt and shell_name in exempt[example_name]:
                continue

            is_exec = (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) & os.stat(shell)[stat.ST_MODE]

            assert is_exec, f"{shell} is not marked as executable"

            func_suffix, _ = os.path.splitext(shell_name)
            functions.append(f'test_{ext}_{func_suffix}')

            with open(shell) as f:
                content = f.read().splitlines()
                assert content[0] == f"#!/usr/bin/env {shell_type}", f"{shell} cannot be executed"

        return functions

    for example, test in tests.items():
        functions = []
        functions.extend(check_and_collect_functions(example, 'sh'))
        functions.extend(check_and_collect_functions(example, 'py'))

        test_content = None
        with open(test, 'r') as test_file:
            test_content = test_file.read()

        assert test_content is not None

        for func in functions:
            assert f'def {func}(' in test_content, f'{test} is missing test function {func}'
