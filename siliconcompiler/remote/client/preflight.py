'''
What `GET /v1` says a server holds, against what a run asks for.

``software`` is a flat map per name and the server resolves over combinations,
so this can only find a listed name at no version a requirement allows. It is
only said: the server's answer at create is the binding one.
'''

from typing import Any, Dict, List

from siliconcompiler.remote.client.errors import clean, listed
from siliconcompiler.remote.environment import canonical

__all__ = ["unmet"]


# What each bucket's entries are called in a message.
_KINDS = {"python": "Python package", "tools": "tool", "interpreter": "interpreter"}


def _satisfied(versions, spec: str) -> bool:
    '''Whether any of ``versions`` meets one PEP 440 specifier set; one that does
    not parse is the server's to refuse.'''
    from packaging.specifiers import InvalidSpecifier, SpecifierSet

    try:
        return any(SpecifierSet(spec).filter(versions, prereleases=True))
    except InvalidSpecifier:
        return True


def _normal(bucket: str, name: str) -> str:
    return canonical(name) if bucket == "python" else name.lower()


def unmet(software: Any, requested: Dict[str, Dict[str, List[str]]]) -> List[str]:
    '''One line per requirement a name the server lists cannot meet.

    A bucket or a name the server did not list is not checked: create decides
    those. An empty list of alternatives means any version.
    '''
    if not isinstance(software, dict):
        return []

    lines = []
    for bucket, requirements in requested.items():
        published = software.get(bucket)
        if not isinstance(published, dict):
            continue
        held = {_normal(bucket, name): versions for name, versions in published.items()
                if isinstance(versions, list)}
        kind = _KINDS.get(bucket, bucket)
        for name, alternatives in sorted(requirements.items()):
            versions = held.get(_normal(bucket, name))
            if versions is not None and alternatives and \
                    not any(_satisfied(versions, spec) for spec in alternatives):
                lines.append(clean(f"{kind} {name} {' or '.join(alternatives)} "
                                   f"(offered: {listed(versions)})"))
    return lines
