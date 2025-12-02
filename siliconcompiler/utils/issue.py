import git
import json
import os
import shutil
import sys
import tarfile
import time
import tempfile

import os.path

from typing import Optional, List, TYPE_CHECKING

from datetime import datetime, timezone

import siliconcompiler

from siliconcompiler.utils import get_file_template
from siliconcompiler.utils.curation import collect
from siliconcompiler.schema_support.record import RecordSchema
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.schema import __version__ as schema_version
from siliconcompiler import __version__ as sc_version
from siliconcompiler.utils.paths import workdir, jobdir, collectiondir

if TYPE_CHECKING:
    from siliconcompiler.project import Project
    from siliconcompiler import Task


def generate_testcase(project: "Project",
                      step: str,
                      index: str,
                      archive_name: Optional[str] = None,
                      archive_directory: Optional[str] = None,
                      include_libraries: bool = True,
                      include_specific_libraries: Optional[List[str]] = None,
                      hash_files: bool = False,
                      verbose_collect: bool = True):
    # Save original schema since it will be modified
    project = project.copy()

    issue_dir = tempfile.TemporaryDirectory(prefix='sc_issue_')

    project.option.set_continue(True)
    if hash_files:
        for key in project.allkeys():
            if key[0] == 'history':
                continue
            if len(key) > 1:
                if key[-2] == 'option' and key[-1] == 'builddir':
                    continue
                if key[-2] == 'option' and key[-1] == 'cachedir':
                    continue
            sc_type: str = project.get(*key, field='type')
            if 'file' not in sc_type and 'dir' not in sc_type:
                continue
            for _, key_step, key_index in project.get(*key, field=None).getvalues():
                project.hash_files(
                    *key,
                    check=False,
                    verbose=False,
                    missing_ok=True,
                    step=key_step, index=key_index)

    manifest_path = os.path.join(issue_dir.name, 'orig_manifest.json')
    project.write_manifest(manifest_path)

    flow = project.option.get_flow()
    tool: str = project.get('flowgraph', flow, step, index, 'tool')
    task: str = project.get('flowgraph', flow, step, index, 'task')

    task_requires: List[str] = project.get('tool', tool, 'task', task, 'require',
                                           step=step, index=index)

    def determine_copy(*keypath: str, in_require: bool):
        copy = in_require

        if keypath[0] == 'library':
            # only copy libraries if selected
            if include_specific_libraries and keypath[1] in include_specific_libraries:
                copy = True
            else:
                copy = include_libraries

            copy = copy and determine_copy(*keypath[2:], in_require=in_require)
        elif keypath[0] == 'history':
            # Skip history
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
            elif keypath[1] == 'credentials':
                # Exclude credentials file
                copy = False

        return copy

    for keypath in project.allkeys():
        if 'default' in keypath:
            continue

        sctype: str = project.get(*keypath, field='type')
        if 'file' not in sctype and 'dir' not in sctype:
            continue

        project.set(
            *keypath,
            determine_copy(*keypath,
                           in_require=','.join(keypath) in task_requires),
            field='copy')

    # Collect files
    work_dir = workdir(project, step=step, index=index)

    builddir = project.option.get_builddir()
    if os.path.isabs(builddir):
        # If build is an abs path, grab last directory
        project.option.set_builddir(os.path.basename(builddir))

    # Temporarily change current directory to appear to be issue_dir
    original_cwd = project._Project__cwd
    project._Project__cwd = issue_dir.name

    # Get new directories
    job_dir = jobdir(project)
    new_work_dir = workdir(project, step=step, index=index)
    collection_dir = collectiondir(project)

    # Restore current directory
    project._Project__cwd = original_cwd

    # Copy in issue run files
    shutil.copytree(work_dir, new_work_dir, dirs_exist_ok=True)
    # Copy in source files
    collect(project, directory=collection_dir, verbose=verbose_collect)

    # Set relative path to generate runnable files
    project._Project__cwd = issue_dir.name

    current_work_dir = os.getcwd()
    os.chdir(new_work_dir)

    flow = project.option.get_flow()

    task_class: "Task" = project.get("tool", tool, "task", task, field="schema")

    with task_class.runtime(SchedulerNode(project, step, index), relpath=new_work_dir) as task_obj:
        # Rewrite replay.sh
        prev_quiet = project.option.get_quiet(step=step, index=index)
        project.option.set_quiet(True, step=step, index=index)
        try:
            # Rerun pre_process
            task_obj.pre_process()
        except Exception:
            pass
        project.option.set_quiet(prev_quiet, step=step, index=index)

        is_python_tool = task_obj.get_exe() is None
        if not is_python_tool:
            task_obj.generate_replay_script(
                f'{workdir(project, step=step, index=index)}/replay.sh',
                '.',
                include_path=False)

        # Rewrite tool manifest
        task_obj.write_task_manifest('.')

    # Restore current directory
    project._Project__cwd = original_cwd
    os.chdir(current_work_dir)

    git_data = {}
    try:
        # Check git information
        repo = git.Repo(path=os.path.join(os.path.dirname(siliconcompiler.__file__), '..'))
        commit = repo.head.commit
        git_data['commit'] = commit.hexsha
        git_data['date'] = time.strftime('%Y-%m-%d %H:%M:%S',
                                         time.gmtime(commit.committed_date))
        git_data['author'] = f'{commit.author.name} <{commit.author.email}>'
        git_data['msg'] = commit.message
        # Count number of commits ahead of version
        version_tag = repo.tag(f'v{siliconcompiler.__version__}')
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

    issue_time = datetime.now(timezone.utc).timestamp()
    issue_information = {}
    issue_information['environment'] = {key: value for key, value in os.environ.items()}
    issue_information['python'] = {"path": sys.path,
                                   "version": sys.version}
    issue_information['date'] = datetime.fromtimestamp(issue_time).strftime('%Y-%m-%d %H:%M:%S')
    issue_information['machine'] = RecordSchema.get_machine_information()
    issue_information['run'] = {'step': step,
                                'index': index,
                                'libraries_included': include_libraries,
                                'tool': tool,
                                'toolversion': project.get('record', 'toolversion',
                                                           step=step, index=index),
                                'task': task}
    issue_information['version'] = {'schema': schema_version,
                                    'sc': sc_version,
                                    'git': git_data}

    if not archive_name:
        design = project.name
        job = project.get('option', 'jobname')
        file_time = datetime.fromtimestamp(issue_time, timezone.utc).strftime('%Y%m%d-%H%M%S')
        archive_name = f'sc_issue_{design}_{job}_{step}_{index}_{file_time}.tar.gz'

    # Make support files
    issue_path = os.path.join(issue_dir.name, 'issue.json')
    with open(issue_path, 'w') as fd:
        json.dump(issue_information, fd, indent=4, sort_keys=True)

    gitignore_path = os.path.join(issue_dir.name, '.gitignore')
    with open(gitignore_path, 'w') as fd:
        fd.write("/*\n")

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
            replay_dir = workdir(project, step=step, index=index, relpath=True)
            issue_title = f'{project.name} for {step}/{index} using {tool}/{task}'
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
                     readme_path,
                     gitignore_path]
        if not is_python_tool and run_path:
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

    project.logger.info(f'Generated testcase for {step}/{index} in: '
                        f'{full_archive_path}')
