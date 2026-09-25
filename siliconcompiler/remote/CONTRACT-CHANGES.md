# Changes to port back into the `v1` contract

`sc-server` is a reference implementation of crucible's `v1` API, so anything
this repo changes about the **published shape** is a change to the contract and
not to a deployment. This file is the running list, kept here rather than in a
commit message because the contract docs live in another tree and the port is a
separate piece of work.

**Where it goes:**
[`api/surface.md`](../../../plans/crucible/orchestration/api/surface.md) for
endpoints and payloads, [`api/database.md`](../../../plans/crucible/orchestration/api/database.md)
for tables and vocabularies, [`api/sc-server-profile.md`](../../../plans/crucible/orchestration/api/sc-server-profile.md)
for what this profile serves.

🔴 **The freeze is the first tagged SC release whose `sc-server` answers
`GET /v1`.** Until then these are free. After it, an additive *response* member
has to be paired with a `GET /v1` capability flag so a client can tell whether
it is there.

⚠️ **`additionalProperties: false` on requests does NOT make an additive
request member cost a version bump.** A server accepting a new optional member
is additive — old clients do not send it. What costs is a client *relying* on
one, which needs a capability flag exactly as a response member does.

---

## Three lists have closed

The nine of the first, the five of the software-buckets review, and the fifteen
of the third — plus the two follow-on decisions after it — were decided in
`crucible/orchestration/api/contract-changes.md`, are implemented here, and
have been removed rather than edited. Their home is the contract now.

---

## Open — not yet in the contract docs

### 1. A `.*` prefix specifier attaches to the release segment only

Implementing *a development client sends `==0.38.10.dev*` rather than an exact
pin*: *the shape is right and that literal is not a specifier.* PEP 440 hangs
`.*` off the release segment and nothing after it, so `packaging` refuses
`==0.38.10.dev*` outright.

**The spelling that works is `==0.38.10.*`**, and it does what was wanted: it
matches every build of that release line, `0.38.10.dev7` and the eventual
`0.38.10` alike, while excluding `0.38.9`.

⚠️ Worth writing down because the intent survives and the example does not, and
an example is what gets copied.

**Where it goes:** `surface.md`, beside the specifier rule.

### 2. A version that parses is not the same as a version that is right

The three probe outcomes — answered, present-but-silent, not there — assume a
tool that answers has answered *usefully*. One does not.

🔴 **`gtkwave --version` without a display prints `Could not initialize GTK!`**,
and its driver took the third word: the catalogue got `initialize` as a
version, from a tool that was present and had said nothing of the sort. The
presence check was right and the parse was wrong, which is a case the three
outcomes have no room for.

✅ **The driver is fixed here** — matched rather than counted, and it raises
naming the display when there is no version in the output, which lands the tool
in `published_date` where it belongs.

⚠️ **But the general shape is worth stating:** a parser given output it did not
expect can return anything, and nothing downstream can tell. This profile warns
when a reported version does not parse as PEP 440 rather than rewriting it —
such a version cannot satisfy a range anyway, so what it needs is an
operator's eye, not a silent correction.

**Proposed:** the profile states that a `reported` version SHOULD parse as PEP
440, and that a deployment which cannot make one do so records it as
`published_date` instead.

**Where it goes:** `sc-server-profile.md`, beside the probe's four traps.
