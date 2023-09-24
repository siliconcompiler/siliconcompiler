import glob
import os


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


def load_manifest(chip, src_file):
    manifest = None
    if (src_file is not None) and (not chip.get('option', 'cfg')):
        # only autoload manifest if user doesn't supply manually
        manifest = _get_manifest(os.path.dirname(src_file))
        if not manifest:
            design = os.path.splitext(os.path.basename(src_file))[0]
            chip.logger.error(f'Unable to automatically find manifest for design {design}. '
                              'Please provide a manifest explicitly using -cfg.')
            return False
    elif not chip.get('option', 'cfg'):
        manifest = _get_manifest_from_design(chip)
        if not manifest:
            chip.logger.error(f'Could not find manifest for {chip.design}')
            return False

    if manifest:
        chip.logger.info(f'Loading manifest: {manifest}')
        chip.read_manifest(manifest)
    return True


def _get_manifest(dirname, design='*'):
    # pkg.json file may have a different name from the design due to the entrypoint
    glob_paths = [os.path.join(dirname, f'{design}.pkg.json'),
                  os.path.join(dirname, 'outputs', f'{design}.pkg.json')]
    manifest = None
    for path in glob_paths:
        manifest = glob.glob(path)
        if manifest:
            manifest = manifest[0]
            break

    if not manifest or not os.path.isfile(manifest):
        return None
    return manifest


def _get_manifest_from_design(chip):
    for jobname, step, index in [
            (chip.get('option', 'jobname'),
             chip.get('arg', 'step'),
             chip.get('arg', 'index')),
            (chip.get('option', 'jobname'),
             None,
             None),
            (chip.schema.get_default('option', 'jobname'),
             chip.get('arg', 'step'),
             chip.get('arg', 'index')),
            (chip.schema.get_default('option', 'jobname'),
             None,
             None)]:
        manifest = _get_manifest(chip._getworkdir(jobname=jobname, step=step, index=index))

        if manifest:
            return manifest
    return None
