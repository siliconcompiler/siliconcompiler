from siliconcompiler.flows import asicflow
from siliconcompiler.flows import asictopflow
from siliconcompiler.flows import drcflow
from siliconcompiler.flows import dvflow
from siliconcompiler.flows import fpgaflow
from siliconcompiler.flows import generate_openroad_rcx
from siliconcompiler.flows import interposerflow
from siliconcompiler.flows import lintflow
from siliconcompiler.flows import screenshotflow
from siliconcompiler.flows import showflow
from siliconcompiler.flows import signoffflow
from siliconcompiler.flows import synflow


def get_flows():
    '''
    Returns a dict of builtin flows
    '''
    return {
        module.__name__.split(".")[-1]: module for module in (
            asicflow,
            asictopflow,
            drcflow,
            dvflow,
            fpgaflow,
            generate_openroad_rcx,
            interposerflow,
            lintflow,
            screenshotflow,
            showflow,
            signoffflow,
            synflow
        )
    }
