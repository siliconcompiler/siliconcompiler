from siliconcompiler.apps import sc_dashboard
from siliconcompiler.apps import sc_install
from siliconcompiler.apps import sc_issue
from siliconcompiler.apps import sc_remote
from siliconcompiler.apps import sc_server
from siliconcompiler.apps import sc_show
from siliconcompiler.apps import sc
from siliconcompiler.apps import smake


def get_apps():
    '''
    Returns a dict of builtin apps
    '''
    return {
        module.__name__.split(".")[-1]: module for module in (
            sc_dashboard,
            sc_install,
            sc_issue,
            sc_remote,
            sc_server,
            sc_show,
            sc,
            smake
        )
    }
