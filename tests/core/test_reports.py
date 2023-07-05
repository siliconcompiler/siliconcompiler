from siliconcompiler.report import report
from siliconcompiler import core
from siliconcompiler import Schema
from siliconcompiler.targets import freepdk45_demo
import os


def test_get_flowgraph_nodes():
    '''
    this ensures that get_flowgraph_nodes correctly records the parts of the
    record, tool, and task with values into a dictionary and does not record
    the parts that have no value.
    '''
    chip = core.Chip(design='s')
    chip.set('option', 'flow', 'optionflow')
    chip.set('record', 'distro', '8', step='import', index='1')

    test = report.get_flowgraph_nodes(chip, 'import', '1')

    assert test == {'distro': '8'}


def test_get_flowgraph_edges():
    '''
    this ensures that get_flowgraph_edges returns a dictionary where the keys
    of the dictionary are tuples representing a node that has given inputs. The
    inputs are the values of these keys which are a set of nodes. Nodes are a
    tuple in the form (step, index).
    '''
    chip = core.Chip(design='')
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
    chip = core.Chip(design='')
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
            if Schema._is_leaf(manifest[key]) or manifest_key == 'default':
                continue
            make_manifest_testing_helper(manifest[key],
                                         test_manifest[key],
                                         manifest_key)

    test = report.make_manifest(chip)
    for key in chip.getkeys():
        make_manifest_testing_helper(chip.schema.cfg, test, key)


def test_make_manifest_leaves():
    '''
    tests that all leaves that have a step and index have there step and index
    concatenated unless the index is 'default' in which case it is just the
    step. If step is 'default' or 'global' the index is simply removed.
    If the pernode is 'never', the value given is the value of the node
    'default'/'default'.
    '''
    chip = core.Chip(design='')
    chip.set('option', 'flow', 'asicflow')
    chip.set('record', 'distro', '8', step='import', index='1')

    # pernode == 'never'
    chip.set('design', 'design_name')

    # index == 'global'
    chip.set('option', 'scheduler', 'msgevent', 'ALL', step='import')

    test = report.make_manifest(chip)

    # concatenated
    assert test['record']['distro']['import1'] == '8'
    # pernode == 'never'
    assert test['design']['value'] == 'design_name'
    # index == 'global'
    assert test['option']['scheduler']['msgevent']['import'] == 'ALL'


def test_get_flowgraph_path():
    '''
    Ensures get_flowgraph_path returns a set of all and only the nodes in the
    'winning' path.
    '''
    chip = core.Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'select', ('place', '1'))

    test = report.get_flowgraph_path(chip)

    assert test == {('place', '1'), ('cts', '0')}


def test_search_manifest_partial_key_search():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on keys.
    '''
    chip = core.Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '8', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, key_search="asi")

    assert 'record' not in filtered_manifest
    assert 'flowgraph' in filtered_manifest


def test_search_manifest_partial_value_search():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on values.
    '''
    chip = core.Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))
    chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '1'))

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest, value_search="8")

    assert 'record' in filtered_manifest
    assert 'flowgraph' not in filtered_manifest


def test_search_manifest_partial_key_and_value_search():
    '''
    Ensures search_manifest is able to filter the manifest for partial matches
    on keys and values simultaneously.
    '''
    chip = core.Chip(design='')
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
    chip = core.Chip(design='')
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
    chip = core.Chip(design='')
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
    chip = core.Chip(design='')
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
    chip = core.Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('record', 'userid', '6', step='import', index='3')

    manifest = report.make_manifest(chip)

    filtered_manifest = report.search_manifest(manifest,
                                               key_search="import1",
                                               value_search="80")

    assert 'distro' in filtered_manifest['record']
    assert 'userid' not in filtered_manifest['record']


def test_get_total_manifest_parameter_count():
    '''
    Ensures get_total_manifest_parameter_count returns the number of keys in
    the manifest returned from make_manifest
    '''
    chip = core.Chip(design='')
    chip.set('option', 'flow', "asicflow")
    chip.set('record', 'distro', '80', step='import', index='1')
    chip.set('record', 'userid', '6', step='import', index='3')

    manifest = report.make_manifest(chip)

    assert report.get_total_manifest_parameter_count(manifest) == 437


def test_get_metrics_source():
    '''
    Ensures get_metrics_source returns a dictionary of all the metrics tracked
    where the key to the dictionary is the file name and the values are a list
    of metrics.
    '''
    chip = core.Chip(design='')
    chip.load_target(freepdk45_demo)
    chip.set('tool', 'openroad', 'task', 'floorplan', 'report',
             'metric', 'this file', step='floorplan', index='0')

    test = report.get_metrics_source(chip, 'floorplan', '0')

    assert test == {'this file': ['metric']}


def add_file_to_reports(filepath, chip):
    try:
        file = open(filepath, "w")
    except FileNotFoundError:
        os.makedirs(filepath[:filepath.rfind('/')])
        file = open(filepath, "w")
    file.write('lsaknfs')
    file.close

    chip.add('tool', 'openroad', 'task', 'floorplan', 'report', 'metric',
             filepath, step='floorplan', index='0')


def test_get_logs_and_reports_filters():
    # need to include folder, files/folders at diff levels, and the correct
    # structure in general. The ordering is important - if folder 'B' is a
    # subfolder or file contained in folder 'A'
    '''
    Ensures get_logs_and_reports returns a dictionary of all and only files and
    folders that are included in the filter. This is all the files in the
    folders inputs, reports, and outputs and files f'{step}.log',
    f'{step}.errors', and f'{step}.warnings'.
    '''
    chip = core.Chip(design='test')
    chip.load_target(freepdk45_demo)
    workdir = chip._getworkdir(step='floorplan', index='0')

    add_file_to_reports(workdir + "/floorplan.log", chip)
    add_file_to_reports(workdir + "/floorplan.errors", chip)
    add_file_to_reports(workdir + "/no_good.errors", chip)
    add_file_to_reports(workdir + "/inputs/all_good.errors", chip)

    test = report.get_logs_and_reports(chip, 'floorplan', '0')

    answer = [(workdir, ['inputs'], ['floorplan.errors', 'floorplan.log']),
              (workdir + '/inputs', [], ['all_good.errors'])]
    not_answer = [(workdir + '/inputs', [], ['all_good.errors']),
                  (workdir, ['inputs'], ['floorplan.errors', 'floorplan.log'])]

    assert test == answer or test == not_answer
