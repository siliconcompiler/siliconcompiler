import git
import json
import os
import shutil
import sys
import tarfile
import time
import tempfile
from datetime import datetime
from siliconcompiler.utils import get_file_template
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler import RecordSchema


def generate_testcase(chip,
                      step,
                      index,
                      archive_name=None,
                      archive_directory=None,
                      include_pdks=True,
                      include_specific_pdks=None,
                      include_libraries=True,
                      include_specific_libraries=None,
                      hash_files=False,
                      verbose_collect=True):
    # Save original schema since it will be modified
    schema_copy = chip.schema.copy()

    issue_dir = tempfile.TemporaryDirectory(prefix='sc_issue_')

    chip.set('option', 'continue', True)
    if hash_files:
        for key in chip.allkeys():
            if key[0] == 'history':
                continue
            if len(key) > 1:
                if key[-2] == 'option' and key[-1] == 'builddir':
                    continue
                if key[-2] == 'option' and key[-1] == 'cachedir':
                    continue
            sc_type = chip.get(*key, field='type')
            if 'file' not in sc_type and 'dir' not in sc_type:
                continue
            for _, key_step, key_index in chip.schema.get(*key, field=None).getvalues():
                chip.hash_files(*key,
                                check=False,
                                allow_cache=True,
                                verbose=False,
                                skip_missing=True,
                                step=key_step, index=key_index)

    manifest_path = os.path.join(issue_dir.name, 'orig_manifest.json')
    chip.write_manifest(manifest_path)

    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow=flow)
    task_requires = chip.get('tool', tool, 'task', task, 'require',
                             step=step, index=index)

    def determine_copy(*keypath, in_require):
        copy = in_require

        if keypath[0] == 'library':
            # only copy libraries if selected
            if include_specific_libraries and keypath[1] in include_specific_libraries:
                copy = True
            else:
                copy = include_libraries

            copy = copy and determine_copy(*keypath[2:], in_require=in_require)
        elif keypath[0] == 'pdk':
            # only copy pdks if selected
            if include_specific_pdks and keypath[1] in include_specific_pdks:
                copy = True
            else:
                copy = include_pdks
        elif keypath[0] == 'history':
            # Skip history
            copy = False
        elif keypath[0] == 'package':
            # Skip packages
            copy = False
        elif keypath[0] == 'tool':
            # Only grab tool / tasks
            copy = False
            if list(keypath[0:4]) == ['tool', tool, 'task', task]:
                # Get files associated with testcase tool / task
                copy = True
                if len(keypath) >= 5:
                    if keypath[4] in ('output', 'input', 'report'):
                        # Skip input, output, and report files
                        copy = False
        elif keypath[0] == 'option':
            if keypath[1] == 'builddir':
                # Avoid build directory
                copy = False
            elif keypath[1] == 'cachedir':
                # Avoid cache directory
                copy = False
            elif keypath[1] == 'cfg':
                # Avoid all of cfg, since we are getting the manifest separately
                copy = False
            elif keypath[1] == 'credentials':
                # Exclude credentials file
                copy = False

        return copy

    for keypath in chip.allkeys():
        if 'default' in keypath:
            continue

        sctype = chip.get(*keypath, field='type')
        if 'file' not in sctype and 'dir' not in sctype:
            continue

        chip.set(*keypath,
                 determine_copy(*keypath,
                                in_require=','.join(keypath) in task_requires),
                 field='copy')

    # Collect files
    work_dir = chip.getworkdir(step=step, index=index)

    builddir = chip.get('option', 'builddir')
    if os.path.isabs(builddir):
        # If build is an abs path, grab last directory
        chip.set('option', 'builddir', os.path.basename(builddir))

    # Temporarily change current directory to appear to be issue_dir
    original_cwd = chip.cwd
    chip.cwd = issue_dir.name

    # Get new directories
    job_dir = chip.getworkdir()
    new_work_dir = chip.getworkdir(step=step, index=index)
    collection_dir = chip._getcollectdir()

    # Restore current directory
    chip.cwd = original_cwd

    # Copy in issue run files
    shutil.copytree(work_dir, new_work_dir, dirs_exist_ok=True)
    # Copy in source files
    chip.collect(directory=collection_dir, verbose=verbose_collect)

    # Set relative path to generate runnable files
    chip._relative_path = new_work_dir
    chip.cwd = issue_dir.name

    current_work_dir = os.getcwd()
    os.chdir(new_work_dir)

    flow = chip.get('option', 'flow')

    task_class = chip.get("tool", tool, field="schema")

    task_class.set_runtime(chip, step=step, index=index)

    # Rewrite replay.sh
    prev_quiet = chip.get('option', 'quiet', step=step, index=index)
    chip.set('option', 'quiet', True, step=step, index=index)
    try:
        # Rerun pre_process
        task_class.pre_process()
    except Exception:
        pass
    chip.set('option', 'quiet', prev_quiet, step=step, index=index)

    is_python_tool = task_class.get_exe() is None

    if not is_python_tool:
        task_class.generate_replay_script(
            f'{chip.getworkdir(step=step, index=index)}/replay.sh',
            '.',
            include_path=False)

    # Rewrite tool manifest
    task_class.write_task_manifest('.')

    # Restore normal path behavior
    chip._relative_path = None

    # Restore current directory
    chip.cwd = original_cwd
    os.chdir(current_work_dir)

    git_data = {}
    try:
        # Check git information
        repo = git.Repo(path=os.path.join(chip.scroot, '..'))
        commit = repo.head.commit
        git_data['commit'] = commit.hexsha
        git_data['date'] = time.strftime('%Y-%m-%d %H:%M:%S',
                                         time.gmtime(commit.committed_date))
        git_data['author'] = f'{commit.author.name} <{commit.author.email}>'
        git_data['msg'] = commit.message
        # Count number of commits ahead of version
        version_tag = repo.tag(f'v{chip.scversion}')
        count = 0
        for c in commit.iter_parents():
            count += 1
            if c == version_tag.commit:
                break
        git_data['count'] = count
    except git.InvalidGitRepositoryError:
        pass
    except Exception as e:
        git_data['failed'] = str(e)
        pass

    tool, task = get_tool_task(chip, step=step, index=index)

    issue_time = time.time()
    issue_information = {}
    issue_information['environment'] = {key: value for key, value in os.environ.items()}
    issue_information['python'] = {"path": sys.path,
                                   "version": sys.version}
    issue_information['date'] = datetime.fromtimestamp(issue_time).strftime('%Y-%m-%d %H:%M:%S')
    issue_information['machine'] = RecordSchema.get_machine_information()
    issue_information['run'] = {'step': step,
                                'index': index,
                                'libraries_included': include_libraries,
                                'pdks_included': include_pdks,
                                'tool': tool,
                                'toolversion': chip.get('record', 'toolversion',
                                                        step=step, index=index),
                                'task': task}
    issue_information['version'] = {'schema': chip.schemaversion,
                                    'sc': chip.scversion,
                                    'git': git_data}

    if not archive_name:
        design = chip.design
        job = chip.get('option', 'jobname')
        file_time = datetime.fromtimestamp(issue_time).strftime('%Y%m%d-%H%M%S')
        archive_name = f'sc_issue_{design}_{job}_{step}{index}_{file_time}.tar.gz'

    # Make support files
    issue_path = os.path.join(issue_dir.name, 'issue.json')
    with open(issue_path, 'w') as fd:
        json.dump(issue_information, fd, indent=4, sort_keys=True)

    readme_path = os.path.join(issue_dir.name, 'README.txt')
    with open(readme_path, 'w') as f:
        f.write(get_file_template('issue/README.txt').render(
            archive_name=archive_name,
            has_run=not is_python_tool,
            **issue_information))

    run_path = None
    if not is_python_tool:
        run_path = os.path.join(issue_dir.name, 'run.sh')
        with open(run_path, 'w') as f:
            replay_dir = os.path.relpath(chip.getworkdir(step=step, index=index),
                                         chip.cwd)
            issue_title = f'{chip.design} for {step}{index} using {tool}/{task}'
            f.write(get_file_template('issue/run.sh').render(
                title=issue_title,
                exec_dir=replay_dir
            ))
        os.chmod(run_path, 0o755)

    full_archive_path = archive_name
    if archive_directory:
        full_archive_path = os.path.join(archive_directory, archive_name)
    full_archive_path = os.path.abspath(full_archive_path)
    # Build archive
    arch_base_dir = os.path.basename(archive_name)
    while arch_base_dir.lower().split('.')[-1] in ('gz', 'tar'):
        arch_base_dir = '.'.join(arch_base_dir.split('.')[0:-1])
    with tarfile.open(full_archive_path, "w:gz") as tar:
        # Add individual files
        add_files = [manifest_path,
                     issue_path,
                     readme_path]
        if not is_python_tool:
            add_files.append(run_path)
        for path in add_files:
            tar.add(os.path.abspath(path),
                    arcname=os.path.join(arch_base_dir,
                                         os.path.basename(path)))

        tar.add(job_dir,
                arcname=os.path.join(arch_base_dir,
                                     os.path.relpath(job_dir,
                                                     issue_dir.name)))

    issue_dir.cleanup()

    chip.logger.info(f'Generated testcase for {step}{index} in: '
                     f'{full_archive_path}')

    # Restore original schema
    chip.schema = schema_copy
