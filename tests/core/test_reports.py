from siliconcompiler.report import report
from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo
import os
from pathlib import Path


def test_get_flowgraph_nodes():
    '''
    this ensures that get_flowgraph_nodes correctly records the parts of the
    record, tool, and task with values into a dictionary and does not record
    the parts that have no value.
    '''
    chip = Chip(design='s')
    chip.set('option', 'flow', 'optionflow')
    chip.set('record', 'distro', '8', step='import', index='1')

    test = report.get_flowgraph_nodes(chip, 'import', '1')

    assert test == {'distro': '8', 'inputnode': '', 'pythonpackage': ''}


def test_get_flowgraph_edges():
    '''
    this ensures that get_flowgraph_edges returns a dictionary where the keys
    of the dictionary are tuples representing a node that has given inputs. The
    inputs are the values of these keys which are a set of nodes. Nodes are a
    tuple in the form (step, index).
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', 'asicflow')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.add('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    test = report.get_flowgraph_edges(chip)

    assert test == {('cts', '0'): {('place', '0'), ('place', '1')}}


def test_make_manifest_branches():
    '''
    tests that all the branches (parts of the tree excluding the leaf) in
    the manifest returned by make_manifest are in the schema and that all
    branches in the schema excluding branches with key 'default' are in the
    manifest returned by make_manifest.
    '''

    def _is_leaf(cfg):
        # 'shorthelp' chosen arbitrarily: any mandatory field with a consistent
        # type would work.
        return 'shorthelp' in cfg and isinstance(cfg['shorthelp'], str)

    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '8', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    def make_manifest_testing_helper(manifest, test_manifest, key):
        assert key in test_manifest
        # all keys in test are in the actual manifest except for keys in the
        # leaf
        for test_manifest_key in test_manifest:
            assert test_manifest_key in manifest
        # all keys in the actual manifest are in the test except for keys in
        # the leaf or keys called 'default'
        for manifest_key in manifest[key]:
            if manifest_key == "__meta__":
                continue
            if _is_leaf(manifest[key]) or manifest_key == 'default':
                continue
            make_manifest_testing_helper(manifest[key],
                                         test_manifest[key],
                                         manifest_key)

    test = report.make_manifest(chip)
    for key in chip.getkeys():
        make_manifest_testing_helper(chip.getdict(), test, key)


def test_make_manifest_leaves():
    '''
    tests that all leaves that have a step and index have there step and index
    concatenated unless the index is 'default' in which case it is just the
    step. If step is 'default' or Parameter.GLOBAL_KEY the index is simply removed.
    If the pernode is PerNode.NEVER, the value given is the value of the node
    'default'/'default'.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', 'asicflow')
    chip.set('record', 'distro', '8', step='import', index='1')

    # pernode == PerNode.NEVER
    chip.set('design', 'design_name')

    # index == Parameter.GLOBAL_KEY
    chip.set('option', 'scheduler', 'msgevent', 'all', step='import')

    test = report.make_manifest(chip)

    # concatenated
    assert test['record']['distro']['import1'] == '8'
    # pernode == PerNode.NEVER
    assert test['design'] == 'design_name'
    # index == Parameter.GLOBAL_KEY
    assert test['option']['scheduler']['msgevent']['import'] == ['all']


def test_get_flowgraph_path():
    '''
    Ensures get_flowgraph_path returns a set of all and only the nodes in the
    'winning' path.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('record', 'inputnode', ('place', '1'), step='cts', index='0')

    test = report.get_flowgraph_path(chip)

    assert sorted(test) == [('cts', '0'), ('place', '1')]


def test_search_manifest_partial_key_search():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on keys.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '8', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, key_search="asi")

    assert 'record' not in filtered_manifest
    assert 'flowgraph' in filtered_manifest


def test_search_manifest_partial_key_search_glob():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on keys.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '8', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, key_search="*sicflow")

    assert 'record' not in filtered_manifest
    assert 'flowgraph' in filtered_manifest


def test_search_manifest_partial_value_search():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on values.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, value_search="8")

    assert 'record' in filtered_manifest
    assert 'flowgraph' not in filtered_manifest


def test_search_manifest_partial_value_search_glob():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on values.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, value_search="*flow")

    assert filtered_manifest == {'option': {'flow': 'asicflow'}}


def test_search_manifest_partial_key_and_value_search():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on keys and values simultaneously.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('record', 'userid', '6', step='import', index='3')

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest,
                                               key_search="import",
                                               value_search="8")

    assert 'distro' in filtered_manifest['record']
    assert 'userid' not in filtered_manifest['record']


def test_search_manifest_no_search():
    '''
    Ensures search_manifest does not filter anything when given no search terms
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('record', 'userid', '6', step='import', index='3')

    manifest = report.make_manifest(chip)

    not_filtered_manifest = report.search_manifest(manifest)

    assert 'distro' in not_filtered_manifest['record']
    assert 'userid' in not_filtered_manifest['record']


def test_search_manifest_complete_key_search():
    '''
    Ensures search_manifest is able to filter the manifest for complete matches
    on keys.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '8', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, key_search="asicflow")

    assert 'record' not in filtered_manifest
    assert 'flowgraph' in filtered_manifest


def test_search_manifest_complete_value_search():
    '''
    Ensures search_manifest is able to filter the manifest for complete matches
    on values.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, value_search="80")

    assert 'record' in filtered_manifest
    assert 'flowgraph' not in filtered_manifest


def test_search_manifest_complete_key_and_value_search():
    '''
    Ensures search_manifest is able to filter the manifest for complete matches
    on keys and values simultaneously.
    '''
    chip = Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('record', 'userid', '6', step='import', index='3')

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest,
                                               key_search="import1",
                                               value_search="80")

    assert 'distro' in filtered_manifest['record']
    assert 'userid' not in filtered_manifest['record']


def test_get_total_manifest_key_count():
    '''
    Ensures get_total_manifest_parameter_key returns the number of keys in
    the manifest returned from make_manifest
    '''
    chip = Chip(design='')

    report_manifest = report.make_manifest(chip)
    org_keys = report.get_total_manifest_key_count(report_manifest)
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('record', 'userid', '6', step='import', index='3')

    manifest = report.make_manifest(chip)
    check_keys = report.get_total_manifest_key_count(manifest)

    assert org_keys + 2 == check_keys


def test_get_metrics_source():
    '''
    Ensures get_metrics_source returns a dictionary of all the metrics tracked
    where the key to the dictionary is the file name and the values are a list
    of metrics.
    '''
    chip = Chip(design='')
    chip.use(freepdk45_demo)
    chip.set('tool', 'openroad', 'task', 'pin_placement', 'report',
             'metric', ['this file', 'that file'],
             step='floorplan.pin_placement', index='0')

    primary, sources = report.get_metrics_source(chip, 'floorplan.pin_placement', '0')

    assert primary == {'this file': ['metric']}
    assert sources == {'this file': ['metric'], 'that file': ['metric']}


def add_file_to_reports(filepath, chip):
    try:
        file = open(filepath, "w")
    except FileNotFoundError:
        os.makedirs(Path(filepath).parent)
        file = open(filepath, "w")
    file.write('lsaknfs')
    file.close

    chip.add('tool', 'openroad', 'task', 'floorplan', 'report', 'metric',
             filepath, step='floorplan', index='0')


def test_get_files():
    '''
    Ensures get_files returns a dictionary of all files and
    folders.
    '''
    chip = Chip(design='test')
    chip.use(freepdk45_demo)
    workdir = chip.getworkdir(step='floorplan', index='0')

    add_file_to_reports(os.path.join(workdir, "floorplan.log"), chip)
    add_file_to_reports(os.path.join(workdir, "floorplan.errors"), chip)
    add_file_to_reports(os.path.join(workdir, "inputs", "all_good.errors"), chip)

    test = report.get_files(chip, 'floorplan', '0')

    answer = [(workdir, {'inputs'}, {'floorplan.log', 'floorplan.errors'}),
              (os.path.join(workdir, 'inputs'), set(), {'all_good.errors'})]

    assert test == answer


def test_get_chart_data_errors():
    '''
    Ensures that if there are more than one unit for a specific metric, a
    TypeError is raised.
    '''
    chip_1 = Chip(design='test')
    chip_1.use(freepdk45_demo)
    chip_2 = Chip(design='test')
    chip_2.use(freepdk45_demo)

    metric = 'cellarea'
    chip_2.set('metric', metric, 'Y', field='unit')

    chip_1.set('metric', metric, '5', step='import', index='0')
    chip_2.set('metric', metric, '6', step='import', index='0')

    try:
        report.get_chart_data([(chip_1, ''), (chip_2, '')], metric,
                              [{'step': 'import', 'index': '0'}])
        # did not raise expected error
        assert False
    except TypeError:
        # did raise expected error
        assert True


def get_chart_data_test_helper(chip_1, chip_1_name, value_1, chip_2,
                               chip_2_name, value_2, metric, step, index):
    chip_1.set('metric', metric, value_1, step=step, index=index)
    chip_2.set('metric', metric, value_2, step=step, index=index)

    return report.get_chart_data([{'chip_object': chip_1, 'chip_name': chip_1_name},
                                  {'chip_object': chip_2, 'chip_name': chip_2_name}],
                                 metric, [(step, index)])


def test_get_chart_data_output():
    '''
    Ensures that get_chart_data returns a a tuple where the first element is a
    2d dictionary of data points, following the forms
    {step+index: {chip_name: value}} where each dictionary can have many keys.
    The second element is a string (or None) that represents the unit.
    '''
    chip_1 = Chip(design='test')
    chip_1.use(freepdk45_demo)
    chip_2 = Chip(design='test')
    chip_2.use(freepdk45_demo)

    step = 'import.verilog'
    index = '0'
    chip_1_name = '1'
    chip_2_name = '2'

    output_cellarea = get_chart_data_test_helper(chip_1, chip_1_name, '5',
                                                 chip_2, chip_2_name, '6',
                                                 'cellarea', step, index)
    output_errors = get_chart_data_test_helper(chip_1, chip_1_name, '5',
                                               chip_2, chip_2_name, '6',
                                               'errors', step, index)
    output_warnings = get_chart_data_test_helper(chip_1, chip_1_name, None,
                                                 chip_2, chip_2_name, None,
                                                 'warnings', step, index)

    assert output_cellarea == ({(step, index): {chip_1_name: 5.0, chip_2_name: 6.0}}, 'um^2')
    assert output_errors == ({(step, index): {chip_1_name: 5, chip_2_name: 6}}, '')
    assert output_warnings == ({}, '')
