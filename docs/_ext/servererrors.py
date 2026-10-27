from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from siliconcompiler.remote.server import errors
from siliconcompiler.schema.docs.utils import build_table, code, link, para, strong


# The remote API's error `type` registry, rendered from the registry itself.
class ServerErrors(SphinxDirective):
    def run(self):
        self.env.note_dependency(errors.__file__)

        entries = [[strong('type'), strong('Status'), strong('Members'), strong('Title')]]
        for err in sorted(errors.ERRORS.values(), key=lambda err: err.slug):
            slug = nodes.paragraph()
            slug += link(err.uri, text=err.slug)
            members = nodes.paragraph()
            for n, member in enumerate(err.members):
                if n:
                    members += nodes.Text(', ')
                members += code(member)
            status = str(err.status) if err.status else 'none'
            entries.append([slug, para(status), members, para(err.title)])

        return build_table(entries, colwidths=[30, 10, 25, 35])


def setup(app):
    app.add_directive('server-errors', ServerErrors)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
