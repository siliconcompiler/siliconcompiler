###############################################
# Configuration schema for `sc-server`
###############################################
def server_schema():
    '''Method for defining Server configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    cfg = {}

    cfg['port'] = {
        'short_help': 'Port number to run the server on.',
        'switch': '-port',
        'switch_args': '<num>',
        'type': ['int'],
        'defvalue': ['8080'],
        'help': ["TBD"]
    }

    cfg['cluster'] = {
        'short_help': 'Type of compute cluster to use. Valid values: [slurm, local]',
        'switch': '-cluster',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue': ['slurm'],
        'help': ["TBD"]
    }

    cfg['nfsmount'] = {
        'short_help': 'Directory of mounted shared NFS storage.',
        'switch': '-nfs_mount',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue': ['/nfs/sc_compute'],
        'help': ["TBD"]
    }

    cfg['auth'] = {
        'short_help': 'Flag determining whether to enable authenticated and encrypted jobs. '
                      'Intended for testing client-side authentication flags, not for '
                      'securing sensitive information.',
        'switch': '-auth',
        'switch_args': '<str>',
        'type': ['bool'],
        'defvalue': [''],
        'help': ["TBD"]
    }

    return cfg
