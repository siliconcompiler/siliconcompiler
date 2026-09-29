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
collected path, as now. It is additive, and leaves `collect(project, keys, ...)`
as #5450 merged it: that signature is settled, since no compatibility path is
coming for it.

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
It recommended a marker in the collection, shared with a layout marker the
compatibility plan would have added; that plan closed as won't-do, so this one
builds its own marker, written by the server as it extracts, or takes another
option.

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

