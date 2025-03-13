import os


# TODO: this is a hack to get around design name requirement: since legal
# design names probably can't contain spaces, we can detect if it is unset.
UNSET_DESIGN = '  unset  '


def manifest_switches():
    '''
    Returns a list of manifest switches that can be used
    to find the manifest based on their values
    '''
    return ['-design',
            '-cfg',
            '-arg_step',
            '-arg_index',
            '-jobname']


def _get_manifests(cwd):
    manifests = {}

    def get_dirs(cwd):
        dirs = []
        for dirname in os.listdir(cwd):
            fullpath = os.path.join(cwd, dirname)
            if os.path.isdir(fullpath):
                dirs.append((dirname, fullpath))
        return dirs

    for _, buildpath in get_dirs(cwd):
        for design, designdir in get_dirs(buildpath):
            for jobname, jobdir in get_dirs(designdir):
                manifest = os.path.join(jobdir, f'{design}.pkg.json')
                if os.path.isfile(manifest):
                    manifests[(design, jobname, None, None)] = manifest
                for step, stepdir in get_dirs(jobdir):
                    for index, indexdir in get_dirs(stepdir):
                        manifest = os.path.join(indexdir, 'outputs', f'{design}.pkg.json')
                        if os.path.isfile(manifest):
                            manifests[(design, jobname, step, index)] = manifest
                        else:
                            manifest = os.path.join(indexdir, 'inputs', f'{design}.pkg.json')
                            if os.path.isfile(manifest):
                                manifests[(design, jobname, step, index)] = manifest

    organized_manifest = {}
    for (design, job, step, index), manifest in manifests.items():
        jobs = organized_manifest.setdefault(design, {})
        jobs.setdefault(job, {})[step, index] = os.path.abspath(manifest)

    return organized_manifest


def pick_manifest_from_file(chip, src_file, all_manifests):
    if src_file is None:
        return None

    if not os.path.exists(src_file):
        chip.logger.error(f'{src_file} cannot be found.')
        return None

    src_dir = os.path.abspath(os.path.dirname(src_file))
    for _, jobs in all_manifests.items():
        for _, nodes in jobs.items():
            for manifest in nodes.values():
                if src_dir == os.path.dirname(manifest):
                    return manifest

    return None


def pick_manifest(chip, src_file=None):
    all_manifests = _get_manifests(os.getcwd())

    manifest = pick_manifest_from_file(chip, src_file, all_manifests)
    if manifest:
        return manifest

    if chip.design == UNSET_DESIGN:
        if len(all_manifests) == 1:
            chip.set('design', list(all_manifests.keys())[0])
        else:
            chip.logger.error('Design name is not set')
            return None

    if chip.design not in all_manifests:
        chip.logger.error(f'Could not find manifest for {chip.design}')
        return None

    if chip.get('option', 'jobname') not in all_manifests[chip.design] and \
            len(all_manifests[chip.design]) != 1:
        chip.logger.error(f'Could not determine jobname for {chip.design}')
        return None

    jobname = chip.get('option', 'jobname')
    if chip.get('option', 'jobname') not in all_manifests[chip.design]:
        jobname = list(all_manifests[chip.design].keys())[0]

    step, index = chip.get('arg', 'step'), chip.get('arg', 'index')
    if step and not index:
        all_nodes = list(all_manifests[chip.design][jobname].keys())
        try:
            all_nodes.remove((None, None))
        except ValueError:
            pass
        for found_step, found_index in sorted(all_nodes):
            if found_step == step:
                index = found_index
        if index is None:
            index = '0'
    if step and index:
        if (step, index) in all_manifests[chip.design][jobname]:
            return all_manifests[chip.design][jobname][(step, index)]
        else:
            chip.logger.error(f'{step}{index} is not a valid node.')
            return None

    if (None, None) in all_manifests[chip.design][jobname]:
        return all_manifests[chip.design][jobname][None, None]

    # pick newest manifest
    return list(sorted(all_manifests[chip.design][jobname].values(),
                       key=lambda file: os.stat(file).st_ctime))[-1]
