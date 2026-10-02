'''The API's routes, one module per part of the surface.'''


def next_page(path: str, cursor: str) -> str:
    '''A collection's `Link` to its next page: this request's query, every
    repeat kept and every value encoded, one page on.'''
    from urllib.parse import urlencode

    import flask

    query = [(name, value) for name, value in flask.request.args.items(multi=True)
             if name != "cursor"] + [("cursor", cursor)]
    return f'<{path}?{urlencode(query)}>; rel="next"'
