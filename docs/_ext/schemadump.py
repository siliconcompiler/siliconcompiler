"""Write a machine-readable dump of the schema to ``schema.json`` at build time.

The schema is the whole configuration surface of SiliconCompiler, and the only
published form of it is the HTML reference: eight hundred parameters rendered as
nested sections. That is the right shape for a person looking one up and the
wrong shape for anything else. Editor tooling, validators, code assistants and
scripts that want to know whether a keypath exists all end up scraping HTML, or
guessing.

This writes the same information as one JSON document at a predictable URL, keyed
by keypath:

.. code-block:: json

   {
     "Project": {
       "description": "...",
       "parameters": {
         "option,fileset": {
           "type": "[str]",
           "pernode": "never",
           "scope": "global",
           "shorthelp": "Option: Selected design filesets",
           "help": "List of filesets to use from the selected design library",
           "defvalue": []
         }
       }
     }
   }

**Which classes are dumped is read out of the reference page itself.** Rather
than keeping a second list of schema roots in sync by hand -- the failure mode
this documentation set has hit repeatedly -- ``reference_manual/schema.rst`` is
parsed for its ``:root:`` options, so the dump covers exactly what the reference
covers, and adding a class to one adds it to the other.

Keypaths are joined with commas, matching the ``:keypath:`option,fileset``` role
and the ``project.get('option', 'fileset')`` call. ``default`` appears as a
literal path segment where the schema takes an arbitrary name -- ``tool,default,
task,default,warningoff`` -- which is how the schema expresses "any tool, any
task".
"""

import enum
import importlib
import inspect
import json
import os
import re

from sphinx.util import logging

import llmstxt

from siliconcompiler.schema import BaseSchema, DocsSchema

logger = logging.getLogger(__name__)

OUTPUT = "schema.json"

# The page whose :root: options define what gets dumped.
REFERENCE = os.path.join("reference_manual", "schema.rst")

_ROOT_OPTION = re.compile(r"^\s*:root:\s*(\S+)\s*$", re.MULTILINE)

# Fields worth publishing. The per-node value tree is deliberately excluded:
# it describes one populated instance rather than the schema, and its defaults
# are already covered by ``defvalue``.
FIELDS = ("type", "scope", "require", "pernode", "switch", "shorthelp", "help",
          "notes", "unit", "copy", "hashalgo", "lock", "example")


def _plain(value):
    """Make a field value JSON-serializable without losing meaning."""
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, set):
        return sorted(_plain(item) for item in value)
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _roots(srcdir):
    """Schema roots named by the reference page, as ``module/Class`` strings."""
    path = os.path.join(srcdir, REFERENCE)
    with open(path, encoding="utf-8") as f:
        found = _ROOT_OPTION.findall(f.read())
    # Preserve document order, drop duplicates.
    roots = list(dict.fromkeys(found))
    if not roots:
        raise ValueError(f"no ':root:' options found in {REFERENCE}; "
                         "schema.json would be empty")
    return roots


def _instances(root):
    """Instantiate a ``module/Class`` root the way the reference renders it."""
    module, name = root.split("/")
    cls = getattr(importlib.import_module(module), name)
    if not (inspect.isclass(cls) and issubclass(cls, BaseSchema)):
        raise TypeError(f"{root} is not a BaseSchema subclass")
    if issubclass(cls, DocsSchema):
        made = cls.make_docs()
        return cls, (made if isinstance(made, list) else [made])
    return cls, [cls()]


def _parameters(schema):
    out = {}
    for keypath in sorted(schema.allkeys()):
        parameter = schema.get(*keypath, field=None)
        entry = {}
        for field in FIELDS:
            try:
                value = parameter.get(field=field)
            except (KeyError, ValueError, TypeError):
                continue
            value = _plain(value)
            # Skip fields that carry no information for this parameter, so a
            # reader is not wading through nulls.
            if value in (None, [], {}, False):
                continue
            entry[field] = value
        try:
            entry["defvalue"] = _plain(parameter.get())
        except Exception:                                      # pragma: no cover
            pass
        out[",".join(keypath)] = entry
    return out


def generate(app, exception):
    # HTML only, for the same reason as llmstxt.py: the file is published from the
    # site root, so no other builder has anywhere to put it.
    if exception is not None or app.builder.name != "html":
        return
    if os.environ.get(llmstxt.SKIP_ENV):
        logger.info("skipping %s (%s is set)", OUTPUT, llmstxt.SKIP_ENV)
        return

    dump = {}
    for root in _roots(app.srcdir):
        cls, instances = _instances(root)
        docstring = inspect.getdoc(cls) or ""
        for instance in instances:
            name = cls.__name__ if len(instances) == 1 else \
                f"{cls.__name__}/{instances.index(instance)}"
            dump[name] = {
                "module": cls.__module__,
                "class": f"{cls.__module__}.{cls.__qualname__}",
                "description": docstring.strip().split("\n\n")[0].replace("\n", " "),
                "parameters": _parameters(instance),
            }

    from siliconcompiler import Project, __version__
    document = {
        "$comment": "Generated dump of the SiliconCompiler schema. "
                    "See https://docs.siliconcompiler.com for prose.",
        "sc_version": __version__,
        "schemaversion": Project().get("schemaversion"),
        "classes": dump,
    }

    path = os.path.join(app.outdir, OUTPUT)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(document, f, separators=(",", ":"), sort_keys=False)

    parameters = sum(len(cls["parameters"]) for cls in dump.values())
    logger.info("wrote %s (%d classes, %d parameters, %.0f kB)",
                OUTPUT, len(dump), parameters, os.path.getsize(path) / 1024)


def setup(app):
    app.connect("build-finished", generate)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
