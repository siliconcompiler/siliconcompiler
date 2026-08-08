/*
 * Custom search scorer, wired up via `html_search_scorer` in conf.py.
 *
 * Sphinx defines `Scorer` in searchtools.js only if it is not already defined;
 * this file is inlined into language_data.js, which every search page loads
 * *after* searchtools.js, so this definition wins.
 *
 * Why this exists: roughly 90% of the searchable headings in this documentation
 * set come from twelve auto-generated pages (the schema reference, the app and
 * API references, and the pre-defined module catalogues). Heading matches are
 * the highest-weighted ranking signal Sphinx has, so without a correction a
 * query for any core concept -- fileset, dataroot, remote, lint -- returns
 * nothing but generated parameter stubs, and the prose that actually explains
 * the concept is unreachable by search.
 *
 * The generated pages remain findable, just below hand-written prose. Anyone
 * who wants a specific schema parameter can search its keypath (for example
 * "option,fileset"), which those sections are titled with.
 */
var Scorer = {
  // Sphinx defaults, restated so this file is the single source of truth.
  objNameMatch: 11,
  objPartialMatch: 6,
  objPrio: { 0: 15, 1: 5, 2: -5 },
  objPrioDefault: 0,
  title: 15,
  partialTitle: 7,
  term: 5,
  partialTerm: 2,

  // Predominantly auto-generated pages, by docname prefix.
  _generated: [
    "reference_manual/schema",          // covers schema and schema_api
    "reference_manual/predef_modules/",
    "reference_manual/apps",
    "reference_manual/server_api",
    "reference_manual/uniquify_api",
    "reference_manual/floorplan_api",
  ],

  /*
   * Applied to every result: heading, object, index-entry and full-text alike.
   *
   * The penalty has to clear the observed generated-heading scores (10-15) to
   * reorder anything; a gentler nudge is indistinguishable from doing nothing.
   */
  score: (result) => {
    const [docname, , , , score] = result;
    if (Scorer._generated.some((p) => docname.startsWith(p))) return score - 12;
    if (docname.startsWith("user_guide/")) return score + 4;
    return score;
  },
};
