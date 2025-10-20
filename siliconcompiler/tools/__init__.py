import inspect

from typing import Union, Type, Callable, Set
from siliconcompiler import Task


def get_task(
        project,
        tool: str = None,
        task: str = None,
        filter: Union[Type[Task], Callable[[Task], bool]] = None) -> Union[Set[Task], Task]:
    """Retrieves tasks based on specified criteria.

    This method allows you to fetch tasks by tool name, task name, or by applying a custom
    filter. If a single task matches the criteria, that task object is returned directly.
    If multiple tasks match, a set of :class:`Task` objects is returned.
    If no criteria are provided, all available tasks are returned.

    Args:
        tool (str, optional): The name of the tool to filter tasks by. Defaults to None.
        task (str, optional): The name of the task to filter by. Defaults to None.
        filter (Union[Type[Task], Callable[[Task], bool]], optional):
            A filter to apply to the tasks. This can be:
            - A `Type[Task]`: Only tasks that are instances of this type will be returned.
            - A `Callable[[Task], bool]`: A function that takes a `Task` object
            and returns `True` if the task should be included, `False` otherwise.
            Defaults to None.

    Returns:
        Union[Set[Task], Task]:
            - If exactly one task matches the criteria, returns that single `Task` object.
            - If multiple tasks match or no specific tool/task is provided (and thus all tasks
            are considered), returns a `Set[Task]` containing the matching tasks.

    Raises:
        ValueError: If no tasks match the specified criteria.
        TypeError: If project is not a Project instance.
    """
    import warnings
    warnings.warn("This function is deprecated and will be removed in a future version, "
                  "use cls.find_task instead", DeprecationWarning, stacklevel=2)

    if filter:
        if inspect.isclass(filter):
            return filter.find_task(project)

    from siliconcompiler import Project
    if not isinstance(project, Project):
        raise TypeError("project must be a Project")

    all_tasks: Set[Task] = set()
    for tool_name in project.getkeys("tool"):
        for task_name in project.getkeys("tool", tool_name, "task"):
            all_tasks.add(project.get("tool", tool_name, "task", task_name, field="schema"))

    tasks = set()
    for task_obj in all_tasks:
        if tool and task_obj.tool() != tool:
            continue
        if task and task_obj.task() != task:
            continue
        if filter:
            if callable(filter):
                if not filter(task_obj):
                    continue
            else:
                raise TypeError("filter is not a recognized type")
        tasks.add(task_obj)

    if not tasks:
        parts = []
        if tool:
            parts.append(f"tool='{tool}'")
        if task:
            parts.append(f"task='{task}'")
        if filter:
            if callable(filter):
                filter_name = getattr(filter, '__name__', repr(filter))
                parts.append(f"filter={filter_name}")
        criteria = ", ".join(parts) if parts else "any criteria"
        raise ValueError(f"No tasks found matching {criteria}")

    if len(tasks) == 1:
        return list(tasks)[0]
    return tasks
