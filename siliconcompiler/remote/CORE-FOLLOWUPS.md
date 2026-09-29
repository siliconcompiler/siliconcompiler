# Follow-ups in SiliconCompiler's core, found from the remote work

The remote client and `sc-server` lean on code outside `remote/`: collection,
the dataroot resolvers, the `Task` interface a driver overrides. Building on it
turns up things that are that code's business rather than this directory's.
They are listed here and not fixed in passing, because each is a decision for
whoever owns the code, and some change behaviour outside a remote run.

This is the companion to [CONTRACT-CHANGES.md](CONTRACT-CHANGES.md): that file
lists changes to the published `v1` shape, and this one lists changes to
SiliconCompiler itself. An item that turns out to change the wire goes there.

**Each item says** what was found, how it was checked, why it matters, the
options, **where it goes**, meaning the code that owns the fix, and where it is
**planned**: a file in the plans repository, each a pull request on `main` that
the owner schedules. When an item is fixed, it is removed, and the commit that
fixes it says so.

---

## Open

### From merging main's collection rework (2026-09-28)

Found while moving this branch onto main's `collect(keys=...)`,
`Task._remote_toolname` and `+private` (#5447, #5448, #5449, #5450).

#### 1. 🔴 A server built from main cannot read an archive from an older client

`#5449` moved collected files from one flat directory,
`<stem>_<sha1("<dataroot>:<parent>")><suffixes>`, to buckets,
`<parent>_<sha1([dataroot, *parent parts])>/<basename>`.
`PathNodeValue.__resolve_collection_path` now looks up only the new layout, and
nothing falls back to the old names.

**Checked:** a file collected under its 0.38.x name, resolved with
`resolve_path(collection_dir=...)` on this branch, raises `FileNotFoundError`.
The old lookup, which listed the flat directory and matched the hashed name,
found it.

**Why it matters:**

- `sc-server` no longer meets it on the wire. It advertises only the
  SiliconCompiler it runs (`images.own_version`), so a client on another
  release is refused at create, `software-unavailable`, rather than having
  every collected file reported missing while staging; and each value's
  collected path is worked out in the manifest's read, by that same
  SiliconCompiler. A server that advertised older releases again would meet
  it.
- Anything collected before the change stops resolving locally too: an
  `sc-issue` testcase made by an older version, and a build directory a
  `-from` run continues from.
- **Nothing records which layout an archive uses.** The 0.57.2 schema bump is
  for `require` alone, so a reader cannot tell the two apart and refuse cleanly.

**Options:**

- A. Keep the old flat names as a fallback in `__resolve_collection_path`,
  tried after the bucket path. This is cheap, and every older archive keeps
  working.
- B. Record the layout, in the manifest or the archive, and have `sc-server`
  refuse the old one as `version-skew`. This is honest, but it drops every
  client release before the change.
- C. Both: read the old layout, and record the new one, so a later change can
  be detected.

**Where it goes:** `siliconcompiler/schema/parametervalue.py`
(`PathNodeValue`), and `siliconcompiler/schema/CHANGELOG.rst` for the layout
change whichever option is taken. It also needs a test that resolves a flat
collection.

**Planned:** [`collect/rework-compatibility.md`](../../../plans/siliconcompiler/collect/rework-compatibility.md),
with item 3. The layout plan chose not to read old collections
([`done/collect-path-layout.md`](../../../plans/siliconcompiler/done/collect-path-layout.md)), so what is
missing is a marker that makes the failure legible.

#### 2. 🔴 Credentials in a URL's query string are not stripped

**Checked:** `owners.strip_userinfo("https://u:tok@host/pdk.tar.gz?access_token=SECRET")`
returns `https://host/pdk.tar.gz?access_token=SECRET`. It removes `user:secret@`
and keeps the query.

**Why it matters:**

- `owners.sources` builds the create descriptor's `sources` with it, so a
  dataroot whose URL carries its token in the query sends that token to the
  server. The contract's rule is that the client MUST strip credentials from
  every URL before sending it (surface *At create*, step 1).
- `Resolver.safe_source` (#5447) keeps the query too, and `Resolver.cache_id`
  is hashed from it. Yet `Resolver._masked_uri` masks every query value in log
  output, so the query is treated as sensitive in one place and as safe in the
  other.

**Options:**

- Drop the query from `safe_source` and from what `owners.sources` sends. Or,
  if a query can be part of a source's identity (a `?ref=`), keep the names and
  drop the values, as `_masked_uri` does.
- Either way, `owners.strip_userinfo` should use `safe_source` rather than keep
  its own rule, so there is one definition.

**Where it goes:** `siliconcompiler/package/__init__.py` (`Resolver.safe_source`),
then `siliconcompiler/remote/owners.py` (`strip_userinfo`, `sources`). This is
also a note in CONTRACT-CHANGES if query names are kept.

**Planned:** [`dataroots/query-credentials.md`](../../../plans/siliconcompiler/dataroots/query-credentials.md).
It recommends dropping the query from what is sent, and making `safe_source` the
one definition. The choice is the owner's, and `strip_userinfo` stays as it is
until it lands on `main`.

#### 3. ⚠️ Released collection API removed without a deprecation wrapper

- `PathNodeValue.get_hashed_filename()` and
  `PathNodeValue.generate_hashed_path()` are gone (#5449). Both shipped in
  every release from v0.28.4 to v0.38.9.
- `collect()` now takes `keys` as a required second positional argument
  (#5450). An old `collect(project)` raises `TypeError`, and
  `collect(project, some_dir)` passes the directory as `keys`. It does not pass
  quietly: it fails when the string is unpacked as a key, or at once for a
  `Path`, with an error that says nothing about the signature.

AGENTS.md (*Renaming or removing public API*) asks for a wrapper that warns and
forwards when a released name goes away.

**Options:**

- Keep `get_hashed_filename()` and `generate_hashed_path()` as deprecated
  names. They can no longer return what they used to, since the layout
  changed, so they should warn and return the bucket path.
- Give `collect` a keyword-only `keys` that defaults to the old behaviour,
  reading `copy`, with a `DeprecationWarning`.

**Where it goes:** `siliconcompiler/schema/parametervalue.py`,
`siliconcompiler/utils/curation.py`.

**Planned:** [`collect/rework-compatibility.md`](../../../plans/siliconcompiler/collect/rework-compatibility.md),
with item 1.

#### 4. ⚠️ `Resolver.is_private` documents a different meaning than a remote run gives it

Its docstring says the source "requires private access (e.g., private
repository or private network location)". A remote run gives every `+private`
source the other meaning the contract has for private: **never leaves the
machine**. It is never uploaded, and is supplied by the operator by name or
refused. That was decided on 2026-09-28 (surface D274). A reader going
by the docstring would expect a `git+ssh+private` repository to be fetched and
uploaded by the client, which is what happens to an unmarked private
repository.

Both meanings are live in code, not only in a docstring: the GitHub resolver
still reads `is_private` as *needs private access* (`package/github.py:93`),
asking for a private release where it is set.

**Where it goes:** `siliconcompiler/package/__init__.py` (`Resolver.is_private`
and the `+private` handling in `Resolver.__init__`), and a line in the
user-facing docs on dataroots.

**Planned:** [`dataroots/private-meaning.md`](../../../plans/siliconcompiler/dataroots/private-meaning.md).

#### 5. ⚠️ Drivers override private names to declare where they run

`Task._remote_toolname` and `Task._remote_inherits_env` (#5448) are how a tool
driver says which image it needs, or that it follows its input node. Plugin
drivers outside this repository need them, and the server reads them
(`runflow.node_tools`, `runflow.inheriting_nodes`,
`setup/server/bootstrap.py`). The leading underscore marks them private, so a
plugin author has to override a private name to get placement right. They also
do not appear in the reference manual.

**Options:** public names, with a docstring on what each default means; or
keep the names and document them as the driver-facing contract they are.

**Where it goes:** `siliconcompiler/tool.py`, and the driver guidance in the
docs.

**Planned:** [`task-api/remote-placement-hooks.md`](../../../plans/siliconcompiler/task-api/remote-placement-hooks.md).
Renaming is free until the next release ships the underscored names.

### From follow-on 15 (2026-09-29)

Found while bringing the branch up to the `v1` changes of 2026-09-29. Each is
SiliconCompiler's to make on `main`, and the branch takes it by merging `main`
once it lands (CONTRACT-CHANGES item 2 names what waits on each).

#### 8. `collect()` cannot pick values within a parameter

The contract keeps an upload per value (surface *A parameter may go up in
part*; client-v1-migration D7): each value goes up where its own dataroot says
it does. `collect(project, keys=[(key, step, index)])` takes a parameter whole,
and resolves it with `BaseSchema._find_files` over every value, so a value that
should stay behind -- a remote PDK not yet in the cache -- is fetched only to be
skipped. Until it can pick, the branch sends a parameter whole and refuses a
private value beside one that goes up (CONTRACT-CHANGES item 1).

**Options:** a keyword-only `select(key, step, index, value) -> bool` that
defaults to every value, which keeps every caller, `sc-issue`'s included,
unchanged. It resolves only the selected values, one at a time as
SiliconCompiler already resolves each (`PathNodeValue.resolve_path`: the
collection directory first, then its own dataroot), and each lands at its own
collected path, as now. It is additive, and stays clear of item 3's options for
`keys`.

**Where it goes:** `siliconcompiler/utils/curation.py` and
`tests/utils/test_curation.py`, as a pull request of its own. Then, on the
branch: `owners.collection_keys` per value, `PrivateBeside` removed, and
`_requested_members` per value.

**Planned:** [`collect/select-values.md`](../../../plans/siliconcompiler/collect/select-values.md).

#### 9. 🔴 A server-side run rebuilds the collection it was uploaded with

**Checked, by reading:** `Scheduler.run` calls `collect()` before the flow
starts wherever a node's scheduler names keys it cannot reach
(`SchedulerNode.collect_keys`): Slurm, where the job's files are outside
`sharedpaths`, which `sc-server` does not set, and Docker on Windows.
`collect()` renames `sc_collected_files` to `sc_previous_collection`, copies
back what the manifest's values name, and deletes the rest.

**Why it matters:** on a job the server extracted, the collection *is* the
upload. A job's helper modules sit in their test's collected folder under
their own names, and no value names them, so a Slurm-dispatched run loses them
and the test fails to import them. The uploaded wheels go too, harmlessly,
since they were installed while the job staged. Host mode and Docker on Linux
never collect, and are unaffected.

**Options:**

- Skip the collect where the collection is already present from an upload: a
  flag the runner sets, or the collection marking itself as complete.
- Have `collect()` keep what it did not write: copy in only what is missing,
  and never delete the previous collection's other files.
- On the server alone, set Slurm's `sharedpaths` to the data directory. It
  avoids the collect only where every file a node reads is under it, which an
  operator's private roots need not be.

**Where it goes:** `siliconcompiler/utils/curation.py` or
`siliconcompiler/scheduler/scheduler.py`. The test Part 9 asks for -- a
server-side run that leaves the uploaded collection intact -- waits for it.

**Planned:** [`collect/uploaded-collection-rebuilt.md`](../../../plans/siliconcompiler/collect/uploaded-collection-rebuilt.md).
It recommends a marker in the collection, shared with item 1's layout marker,
and written by the server as it extracts.

#### 10. A package's dataroot is decided again wherever the object is built

`PythonPathResolver.set_dataroot` chooses between `python://<module>` and the
package's remote source by asking `is_python_module_editable`, each time the
object is built. The client's choice is what the upload was made from: an
editable package's files are uploaded, and its code goes up as a wheel.

**Why it matters, by reading:** on the node the package is installed from that
wheel into the job's environment, which is on the tool's `PYTHONPATH` only and
never on SiliconCompiler's own, so the node's SiliconCompiler cannot import it
to resolve `python://<module>`, and asking whether it is editable there answers
a different question. The surface says a dataroot the client resolved to local
files resolves on the node to the uploaded copy, never by asking whether the
package there is installed editable (*Uploaded wheels*).

⚠️ **Narrower than this said, by reading `main`:**

- **A manifest load keeps the client's choice.** It instantiates each class,
  which runs `set_dataroot` again, and then repopulates every value from the
  manifest (`BaseSchema._from_dict`), so the choice the client made survives.
  What is left is an object built fresh on the node, and a `python://`
  dataroot resolved there directly.
- **lambdapdk makes no editable check of its own.** It calls `set_dataroot`,
  and decides only its ref.
- **Next step: reproduce the defect** before building the fix.

**Options:** record the client's choice in the manifest, and on the node:
never re-run it when an object is rebuilt from the manifest; resolve a
dataroot the client resolved to local files to its copy in the collection,
never by importing the module; and keep the editable decision in that one
resolver.

**Where it goes:** `siliconcompiler/package/__init__.py`
(`PythonPathResolver`), and lambdapdk. The test Part 9 asks for -- an editable
package whose dataroot resolves to the uploaded copy on the node, with the
network off -- waits for it.

**Planned:** [`dataroots/decided-once.md`](../../../plans/siliconcompiler/dataroots/decided-once.md).

#### 11. `collect()` follows links, and stores a file once per value that names it

**Checked:** a directory value holding `alias.vh -> defs.vh` is collected as
two regular files, and a file that two values name under two dataroots
(`rtl/a.v` under `top`, `a.v` under `rtl`, one file) is collected twice, once in
each value's folder. `shutil.copytree` follows links by default, so a link out
of the directory brings its target's bytes in too.

**Why it matters:** contract.md says an upload keeps links, and stores a
linked file once. A remote run uploads the collection, so the same bytes go up
twice, and a link out of a design's own directory -- into a PDK, say -- sends
what it points at.

**Options:** copy directories with `symlinks=True`, keeping a link whose target
is in the collection as a link to the target's collected copy; store a file
whose home is outside the collection once, at its first appearance, as
contract.md does for an upload, rather than leaving out or refusing a link that
leaves its directory -- only an archive the server produces drops one; and store
a file two values name once, the second as a link to the first.

**Where it goes:** `siliconcompiler/utils/curation.py`.

**Planned:** [`collect/store-once.md`](../../../plans/siliconcompiler/collect/store-once.md).

#### 12. 🔴 A file inside an already-collected directory is skipped, and then resolves nowhere

**Checked, reproduced on `main` at `e86772186e`:** a file whose value sits
inside a directory already collected is skipped (`utils/curation.py:193-201`),
because it is *"reachable via the collected directory's search path"* -- even
when the file's value is under another dataroot. Resolution goes by the value's
own dataroot, so once the sources are gone the file resolves nowhere. With
dataroot `top` at `proj/`, dataroot `rtl` at `proj/rtl/`, an `idir` of `rtl`
under `top` and a file `a.v` under `rtl`, `a.v` is not in the collection.

**Why it matters:** `collect()` reports no error, and the run fails on
whichever machine does not have the original: the server, or an `sc-issue`
testcase opened elsewhere. It predates the rework: `v0.38.9` has the same skip.

**Options:** give such a value a link at its own collected path to the copy
already stored, never a skip -- the same step as storing a file once for item
11.

**Where it goes:** `siliconcompiler/utils/curation.py`.

**Planned:** [`collect/store-once.md`](../../../plans/siliconcompiler/collect/store-once.md), with item 11.

