'''
What `GET /v1` says a run cannot have, said before a job exists.

``software`` is a flat map per name and the server resolves over combinations,
so this can only find a requirement nothing offered satisfies: the server's
answer at create is still the binding one, and this only moves it before a job
row and an upload.
'''

from typing import Any, Dict, List

from siliconcompiler.remote.client.errors import clean, listed
from siliconcompiler.remote.environment import canonical

__all__ = ["unmet", "lacks_feature"]


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
    '''One line per requirement the published ``software`` cannot meet.

    A bucket the server did not publish is not checked. An empty list of
    alternatives means any version, so only the name has to be held.
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
            if versions is None:
                lines.append(clean(f"no {kind} {name} here (offered: {listed(held)})"))
            elif alternatives and not any(_satisfied(versions, spec) for spec in alternatives):
                lines.append(clean(f"{kind} {name} {' or '.join(alternatives)} "
                                   f"(offered: {listed(versions)})"))
    return lines


def lacks_feature(published: Any, feature: str) -> bool:
    '''Whether `GET /v1` was read and does not list ``feature``.'''
    features = published.get("features") if isinstance(published, dict) else None
    return isinstance(features, list) and feature not in features
