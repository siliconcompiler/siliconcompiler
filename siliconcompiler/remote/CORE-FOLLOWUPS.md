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

### From merging `main`'s #5465 (2026-10-01)

#### 14. 🔴 A dataroot whose source carries a query is collected under one name and looked for under another

**Checked, by construction:** `main`'s #5465 buckets each collected file by
its dataroot's `collection_id`, a hash of the source and reference "as the
manifest records them" (`Resolver._collection_source`): userinfo dropped, the
query kept whole. Surface D302 has the client mask every query value in the
manifest it uploads. So for `https://example.com/ip/archive/?token=SECRET` the
client collects under the id of `?token=SECRET` and the server, reading the
masked manifest, looks under the id of `?token=***`: different buckets. For
userinfo alone both agree, since the id drops it either way.

**Why it matters:** a value under such a dataroot that goes up is not found
where it arrived. The server takes it as never sent and asks for it, the client
sends the same bytes to the same place, and the run fails on *asked again for
what was sent*. Two cases upload one: a design's own dataroot on a remote
source, which always uploads, and a remote source the server asked for. A
presigned or tokened download URL is the ordinary way to have one.

**Options:**

- The id hashes the source with every query value masked, as `safe_source`
  writes it, so it is what both ends can compute from the uploaded manifest. Two
  sources differing only in a query value then share a bucket; the reference,
  not the query, is the usual version, and one object presigned twice would
  share one bucket rather than taking two.
- The manifest records each dataroot's `collection_id` as the client computed
  it, and the reader uses the recorded one. A schema field, and the server
  trusting a value the client wrote, which the collection layout is meant to
  derive.
- The client keeps the query values of a dataroot whose files it uploads. That
  is what D302 forbids.

**Where it goes:** `siliconcompiler/package/__init__.py`
(`Resolver._collection_source`, `collection_id`).

**Planned:** not yet; nothing in the plans repository covers it.
