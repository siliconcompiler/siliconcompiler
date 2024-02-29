import os


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
            pass

    tests = []
    for f in os.listdir(test_folder):
        path = os.path.join(test_folder, f)
        if os.path.isfile(path):
            tests.append(f)
            pass

    for test in tests:
        assert test in expected_test_files, f"Extra test found: {test}"

    for test in expected_test_files:
        assert test in tests, f"Missing test found: {test}"
