# Follow-ups in SiliconCompiler's core, found from the remote work

The remote client and `sc-server` lean on code outside `remote/`: collection,
the dataroot resolvers, the `Task` interface a driver overrides. Building on it
turns up things that are that code's business rather than this directory's.
They are listed here and not fixed in passing, because each is a decision for
whoever owns the code, and some change behaviour outside a remote run.

This is the companion to [CONTRACT-CHANGES.md](CONTRACT-CHANGES.md): that file
lists changes to the published `v1` shape, and this one lists changes to
SiliconCompiler itself. An item that turns out to change the wire goes there.

**Each item says** what was found and where it is **planned**: a file in the
plans repository, each a pull request on `main` that the owner schedules, which
holds how it was checked, why it matters, the options and the code that owns
the fix. An item with no plan yet carries those here until it has one. When an
item is fixed, it is removed, and the commit that fixes it says so.

---

## Open

Each is SiliconCompiler's to make on `main`, planned in the plans repository,
and the branch takes it by merging `main` once it lands. The numbers stay, since
CONTRACT-CHANGES item 2 names them.

- **9. A server-side run rebuilds the collection it was uploaded with**, losing
  a job's helper modules where a Slurm-dispatched run collects before it
  starts. Planned:
  [`collect/uploaded-collection-rebuilt.md`](../../../plans/siliconcompiler/collect/uploaded-collection-rebuilt.md).
- **10. A package's dataroot is decided again wherever the object is built**,
  where the node should resolve the uploaded copy. Planned:
  [`dataroots/decided-once.md`](../../../plans/siliconcompiler/dataroots/decided-once.md).
- **14. A dataroot whose source carries a query is collected under one
  `collection_id` and looked for under another**, since the client hashes the
  query as written and the server the masked one. Planned:
  [`dataroots/masked-query-bucket.md`](../../../plans/siliconcompiler/dataroots/masked-query-bucket.md).
