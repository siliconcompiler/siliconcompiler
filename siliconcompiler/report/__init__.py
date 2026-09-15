from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siliconcompiler.report.summary_image import _open_summary_image, generate_summary_image
    from siliconcompiler.report.dashboard.web import WebDashboard

__all__ = [
    "_open_summary_image",
    "WebDashboard",
    "generate_summary_image"
]

# Where each lazily re-exported name actually lives.
_LAZY_EXPORTS = {
    "_open_summary_image": "siliconcompiler.report.summary_image",
    "generate_summary_image": "siliconcompiler.report.summary_image",
    "WebDashboard": "siliconcompiler.report.dashboard.web",
}


def __getattr__(name):
    """Resolve the package's re-exports on first access (PEP 562).

    Binding them eagerly meant that reaching any module under
    ``siliconcompiler.report`` -- the CLI dashboard and the email templates both
    do -- loaded Pillow and the web dashboard as a side effect of the parent
    package. Both are only needed by the summary image and ``sc-dashboard``.
    """
    module = _LAZY_EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    import importlib

    value = getattr(importlib.import_module(module), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
