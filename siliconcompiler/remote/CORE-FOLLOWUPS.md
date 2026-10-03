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

Nothing open.
