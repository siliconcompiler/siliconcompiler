#!/usr/bin/env python3
"""Measure on-site search relevance against a built ``searchindex.js``.

Roughly 90% of the searchable headings in this documentation set come from a
handful of auto-generated pages, and heading matches are the highest-weighted
ranking signal Sphinx has. Without a correction, a query for any core concept
returns generated parameter stubs and the prose that explains the concept is
unreachable by search.

That ratio only moves in one direction on its own: every new tool, PDK, library,
and schema parameter adds generated headings, while prose is added by hand. This
script exists so the balance can be re-measured rather than assumed.

Usage::

    cd docs && rm -rf _build && make html
    python3 _ext/searchrank.py _build/html/searchindex.js

Measure from a clean build. An incremental build reuses cached index data for
pages it did not rebuild, which is enough to shift rankings by a place or two.

This is a port of the ranking in ``sphinx/themes/basic/static/searchtools.js``
(``Search._performSearch`` plus ``performTermsSearch``) together with the
``Scorer.score`` hook supplied by ``_static/search_scorer.js``. It deliberately
omits the object-search branch, which only fires for API-shaped queries.
"""

import json
import pathlib
import sys

import snowballstemmer

# ``terms`` and ``titleterms`` are keyed by stem, not by word, so the query has
# to be stemmed the same way before it can be looked up. Sphinx's English search
# language uses the Porter stemmer; searchtools.js runs a JavaScript port of the
# same algorithm in the browser. Skipping this step silently under-reports every
# query whose stem differs from the word ("credentials" -> "credenti").
_STEMMER = snowballstemmer.stemmer("porter")

# Predominantly auto-generated pages, by docname prefix. Keep in sync with
# the _generated list in docs/_static/search_scorer.js.
GENERATED = (
    "reference_manual/schema",          # covers schema and schema_api
    "reference_manual/predef_modules/",
    "reference_manual/apps",
    "reference_manual/server_api",
    "reference_manual/uniquify_api",
    "reference_manual/leflib_api",
)

# Sphinx's default Scorer weights (searchtools.js).
TITLE, TERM, PARTIAL_TITLE, PARTIAL_TERM = 15, 5, 7, 2

# Concepts a stuck reader is most likely to type. Each should surface prose,
# not a schema stub, when prose on the topic exists.
QUERIES = ["fileset", "dataroot", "remote", "lint", "sky130", "install",
           "smake", "check_manifest", "drvs", "credentials", "builddir"]


def load(path):
    text = pathlib.Path(path).read_text()
    return json.loads(text[text.index("(") + 1:text.rindex(")")])


def is_generated(docname):
    return docname.startswith(GENERATED)


def scorer(score, docname):
    """Mirror of the score() hook in docs/_static/search_scorer.js."""
    if is_generated(docname):
        return score - 12
    if docname.startswith("user_guide/"):
        return score + 4
    return score


def search(idx, query, apply_scorer=True):
    """Return ranked ``[score, docname, title]`` rows for a query."""
    docnames, titles = idx["docnames"], idx["titles"]
    q = query.lower().strip()
    results = []

    for title, found in idx["alltitles"].items():
        if q in title.lower().strip() and len(q) >= len(title) / 2:
            for file, _anchor in found:
                score = round(TITLE * len(q) / len(title))
                score += 1 if titles[file] == title else 0    # document-title boost
                shown = title if titles[file] == title else f"{titles[file]} > {title}"
                results.append([score, docnames[file], shown])

    # Index entries. Non-main entries are collected separately: searchtools.js
    # displays them after every other result regardless of score, on the grounds
    # that they are usually incidental cross-references. A search hint therefore
    # has to be a main entry ("!" in the index directive) to be worth adding.
    non_main = []
    for entry, found in idx["indexentries"].items():
        if q in entry.lower() and len(q) >= len(entry) / 2:
            for file, _anchor, is_main in found:
                row = [round(100 * len(q) / len(entry)), docnames[file], titles[file]]
                (results if is_main else non_main).append(row)

    # Full-text. This is where prose competes with the generated tree.
    best = {}

    def add(files, score):
        if files is None:
            return
        if not isinstance(files, list):
            files = [files]
        for file in files:
            best[file] = max(best.get(file, 0), score)

    terms, titleterms = idx["terms"], idx["titleterms"]
    stem = _STEMMER.stemWord(q)
    add(terms.get(stem), TERM)
    add(titleterms.get(stem), TITLE)
    if len(q) > 2:
        if stem not in terms:
            for term, files in terms.items():
                if q in term:
                    add(files, PARTIAL_TERM)
        if stem not in titleterms:
            for term, files in titleterms.items():
                if q in term:
                    add(files, PARTIAL_TITLE)
    for file, score in best.items():
        results.append([score, docnames[file], titles[file]])

    if apply_scorer:
        for row in results + non_main:
            row[0] = scorer(row[0], row[1])

    results.sort(key=lambda row: (-row[0], row[2]))
    non_main.sort(key=lambda row: (-row[0], row[2]))
    return results + non_main


def main(path, apply_scorer=True):
    idx = load(path)
    entries = sum(len(v) for v in idx["alltitles"].values())
    generated = sum(1 for v in idx["alltitles"].values() for file, _ in v
                    if is_generated(idx["docnames"][file]))
    print(f"{len(idx['docnames'])} documents, {entries} heading entries, "
          f"{100 * generated // entries}% from auto-generated pages")

    dupes = sorted(((len(v), t) for t, v in idx["alltitles"].items()), reverse=True)[:5]
    print("most-duplicated headings: "
          + ", ".join(f"{title!r} x{n}" for n, title in dupes))

    print(f"\n{'query':<16}{'hits':>6}{'gen/top10':>11}   first prose result")
    print("-" * 72)
    worst = 0
    for query in QUERIES:
        results = search(idx, query, apply_scorer)
        if not results:
            print(f"{query:<16}{0:>6}{'-':>11}   (no results)")
            continue
        top = results[:10]
        gen_top = sum(1 for row in top if is_generated(row[1]))
        rank = next((i + 1 for i, row in enumerate(results) if not is_generated(row[1])), None)
        worst = max(worst, rank or 0)
        where = f"#{rank} {results[rank - 1][1]}" if rank else "none (no prose on this topic)"
        print(f"{query:<16}{len(results):>6}{f'{gen_top}/{len(top)}':>11}   {where}")

    print(f"\nworst prose rank across the query set: {worst}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], "--no-scorer" not in sys.argv))
