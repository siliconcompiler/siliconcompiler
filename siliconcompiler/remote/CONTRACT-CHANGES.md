# Changes to port back into the `v1` contract

`sc-server` is a reference implementation of crucible's `v1` API, so anything
this repo changes about the **published shape** is a change to the contract and
not to a deployment. This file is the running list, kept here rather than in a
commit message because the contract docs live in another tree and the port is a
separate piece of work.

**Where it goes:**
[`api/surface.md`](../../../plans/crucible/orchestration/api/surface.md) for
endpoints and payloads, [`api/database.md`](../../../plans/crucible/orchestration/api/database.md)
for tables and vocabularies. What this profile serves is `sc-server`'s own, in
[`setup/server/PROFILE.md`](../../setup/server/PROFILE.md): a change there needs
no port. Changes to SiliconCompiler's own code that the remote work turns up go
in [CORE-FOLLOWUPS.md](CORE-FOLLOWUPS.md) instead.

A finding is a change to the published shape: before the freeze any part of
`v1` may change, and a new request member is paired with a `features` string
([contract.md §2](../../../plans/crucible/orchestration/api/contract.md#2-versioning-put-it-in-the-path)).

---

Closed items are removed from this file. Their decisions are in the contract
docs' decision records, and this file's history records when each went.

## Open

Nothing open.
