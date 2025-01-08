from siliconcompiler.checklists import oh_tapeout


def get_checklists():
    '''
    Returns a dict of builtin checklists
    '''
    return {
        module.__name__.split(".")[-1]: module for module in (
            oh_tapeout,
        )
    }
