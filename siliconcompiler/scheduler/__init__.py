from typing import TYPE_CHECKING

from siliconcompiler.scheduler.error import SCRuntimeError
from siliconcompiler.scheduler.schedulernode import SchedulerNode
from siliconcompiler.scheduler.slurm import SlurmSchedulerNode
from siliconcompiler.scheduler.taskscheduler import TaskScheduler
from siliconcompiler.scheduler.scheduler import Scheduler

if TYPE_CHECKING:
    from siliconcompiler.scheduler.docker import DockerSchedulerNode

__all__ = [
    "Scheduler",
    "SchedulerNode",
    "TaskScheduler",
    "DockerSchedulerNode",
    "SlurmSchedulerNode",
    "SCRuntimeError"
]


def __getattr__(name):
    """Resolve :class:`DockerSchedulerNode` on first access (PEP 562).

    Importing it eagerly pulls in the ``docker`` package, which is the single
    most expensive import in the tree and is only needed when a node actually
    selects the docker scheduler.
    """
    if name == "DockerSchedulerNode":
        from siliconcompiler.scheduler.docker import DockerSchedulerNode

        globals()[name] = DockerSchedulerNode
        return DockerSchedulerNode
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
