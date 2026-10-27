.. _remote_api:

Remote API
==========

This page specifies the ``v1`` HTTP API between SiliconCompiler's remote client
and a job server: what a client sends, and what a server must answer. It is
written for anyone building a server the client can use, or a client of their
own. To run jobs remotely, see :ref:`remote_processing`.

.. note::

  ``v1`` is **alpha**. It is versioned, but any part of it may change until it
  is declared frozen, and nothing on the wire marks the freeze. Building another
  ``v1`` server before then is discouraged.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be interpreted
as described in :rfc:`2119` and :rfc:`8174`. The API constrains what a client
can observe; how a server stores, schedules and isolates the work behind it is
its own business.

Overview
--------

A remote run is submit, poll, collect:

.. code-block:: text

  GET  /v1                              which versions the server runs, which login it takes
  POST /v1/auth/token                   a session, bound to this machine's key
  POST /v1/jobs                         201, the job in created
  POST /v1/jobs/{id}/upload-grant       200, a presigned PUT
  PUT  <the presigned URL>              the archive, straight to storage
  POST /v1/jobs/{id}/submit             202, the job in staging
  GET  /v1/jobs/{id}                    until terminal, waiting Retry-After between reads
  GET  /v1/jobs/{id}/logs?step=&index=  303 to one node's live log
  GET  /v1/jobs/{id}/artifacts          the results, listed
  GET  /v1/jobs/{id}/artifacts/{aid}    303 to one artifact's bytes

* Every path is under ``/v1``. The API moves JSON and never bulk bytes: an
  archive goes up, and every artifact comes down, through a URL the server
  hands over.
* Every session is bound to a key pair the client generates and keeps. Each
  request carries a token and a proof signed with that key
  (:ref:`DPoP <remote_api_dpop>`).
* The create call carries what the client already knows about the run, so a
  job can be refused before its archive moves.

.. list-table::
  :header-rows: 1
  :widths: 45 20 35

  * - Endpoint
    - Credential
    - Scope
  * - :ref:`GET /v1 <remote_api_capabilities>`
    - none
    - --
  * - :ref:`GET /v1/healthz <remote_api_healthz>`
    - none
    - --
  * - :ref:`POST /v1/auth/device <remote_api_device>`
    - a DPoP proof
    - --
  * - :ref:`POST /v1/auth/token <remote_api_token>`
    - a DPoP proof
    - --
  * - :ref:`POST /v1/auth/revoke <remote_api_revoke>`
    - token
    - none: a session may always end itself
  * - :ref:`POST /v1/auth/browser <remote_api_browser>`
    - token
    - none; refused to a CI session
  * - :ref:`GET /v1/me <remote_api_me>`
    - token
    - ``profile:read``
  * - :ref:`GET /v1/devices <remote_api_devices>`
    - token
    - ``devices:read``
  * - ``GET /v1/devices/{id}``
    - token
    - ``devices:read``
  * - ``DELETE /v1/devices/{id}``
    - token
    - ``devices:write``
  * - :ref:`POST /v1/jobs <remote_api_create>`
    - token
    - ``jobs:write``
  * - :ref:`POST /v1/jobs/{id}/upload-grant <remote_api_grant>`
    - token
    - ``jobs:write``
  * - :ref:`POST /v1/jobs/{id}/submit <remote_api_submit>`
    - token
    - ``jobs:write``
  * - :ref:`GET /v1/jobs <remote_api_list>`
    - token
    - ``jobs:read``
  * - :ref:`GET /v1/jobs/{id} <remote_api_job>`
    - token
    - ``jobs:read``
  * - :ref:`POST /v1/jobs/{id}/cancel <remote_api_cancel>`
    - token
    - ``jobs:write``
  * - :ref:`DELETE /v1/jobs/{id} <remote_api_delete>`
    - token
    - ``jobs:delete``
  * - :ref:`GET /v1/jobs/{id}/logs <remote_api_logs>`
    - token
    - ``jobs:read``
  * - :ref:`GET /v1/jobs/{id}/artifacts <remote_api_artifacts>`
    - token
    - ``jobs:read``
  * - :ref:`GET /v1/jobs/{id}/artifacts/{artifact_id} <remote_api_fetch>`
    - token
    - ``artifacts:read``

Nothing else is under ``/v1/``. ``/v1/admin/`` is reserved for a deployment's
own routes and is never given to the API, so they cannot collide with it; a
route there MUST NOT accept a ``v1`` access token, and no ``v1`` scope is
administrative. A deployment's portal is outside ``/v1`` and its routes are not
part of the API: a client reaches a portal page only through a URL the server
hands it.

There is deliberately no webhook, no ``.well-known`` discovery document, no
separate refresh endpoint, no retry verb (a retried request replays through
``Idempotency-Key``; a new run is a new job) and no path into an archive.

Conventions
-----------

Versioning and compatibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The version is in the path. Within ``v1`` a change is additive only: new
response members, new endpoints, and new optional request members, each paired
with a ``features`` string in ``GET /v1``, since an older server refuses a
member it does not know. Nothing is removed, retyped or tightened.

**Requests are strict.** A JSON endpoint refuses a request member it does not
define, and every endpoint refuses a query parameter it does not define, with
``400 invalid-request``. A client-supplied value is checked for type, length and
character set and refused rather than trimmed or escaped; the refusal names the
field and never echoes the value. The two OAuth endpoints are the exception: they
ignore a parameter they do not know (:rfc:`6749#section-3.2`), except
``actor_token``, ``audience`` and ``resource``, which are refused
``invalid_request``.

**Responses are must-ignore.** A client discards a response member it does not
know. It also accepts an unrecognised value in an enumerated field, and takes
the cautious default:

.. list-table::
  :header-rows: 1
  :widths: 35 65

  * - Field
    - On a value the client does not recognise
  * - a job's or node's ``state``
    - read ``terminal``, and keep polling while it is ``false``
  * - an SSE ``event:``
    - discard the event
  * - ``end.reason`` on a log stream
    - re-request the stream and resume; only ``terminal`` means stop
  * - an artifact's ``kind``
    - list it, and infer nothing from it
  * - ``terms[].scope.applies_to``
    - infer no block either way
  * - ``deleted_cause``
    - report the artifact deleted, reason unknown
  * - ``notices[].level``
    - treat it as ``warning``
  * - ``identity_assurance``
    - do not rely on the identity
  * - a granted scope
    - ignore it
  * - ``WWW-Authenticate``'s ``error=``
    - fail, and say so
  * - an error ``type``
    - an untyped failure of its status class, retried by waiting only where it
      carries ``Retry-After``
  * - ``reason`` on a known ``type``
    - act on the ``type`` alone
  * - anything else
    - display the raw value, and act on nothing

Every enumeration is closed at ``v1``, so these defaults are robustness rather
than room to grow. The exceptions are artifact kinds and scopes, which ``v1``
may add to. The error registry is complete at the freeze.

**Deprecation.** A deprecated version answers every response with
``Deprecation`` and ``Sunset`` headers, at least 60 days apart. A client MUST
NOT fail on either, and warns its user once per session, giving the
``Sunset`` date.

Requests and responses
^^^^^^^^^^^^^^^^^^^^^^

* A success is ``application/json``, and a refusal ``application/problem+json``
  (:ref:`remote_api_errors`). A live log is ``text/event-stream``, from the
  stream host rather than the API.
* There is no envelope: a resource response is the resource. A collection is
  ``{"items": [...]}``, and an empty one is ``200`` with ``{"items": []}``,
  never ``404``.
* ``201`` carries the resource and a ``Location`` header. ``202`` carries the
  resource in its new state, so a client need not read it again. ``204`` carries
  nothing.
* A request shown below as ``{}`` takes no body. A server accepts an empty body
  and a JSON ``{}`` alike there.
* JSON request bodies are ``application/json``. The two OAuth endpoints take
  ``application/x-www-form-urlencoded``.

Names and values
^^^^^^^^^^^^^^^^

.. list-table::
  :header-rows: 1
  :widths: 30 70

  * - Form
    - Means
  * - ``snake_case``
    - every member, query parameter and enumeration value
  * - ``kebab-case``
    - an error ``type`` slug, ``limit-exceeded``
  * - lowercase, dot-separated
    - a feature string, ``logs.stream``
  * - ``<resource>:<action>``
    - a scope, ``jobs:read``
  * - ``..._at``
    - an :rfc:`3339` timestamp in UTC, written with ``Z``
  * - ``..._until``
    - a timestamp promised as a floor
  * - ``..._seconds``, ``..._bytes``, ``..._count``
    - a number in that base unit, never scaled
  * - ``max_...``
    - a ceiling on one request or one object
  * - ``concurrent_...``, ``pending_...``
    - a ceiling on what one caller holds at once, in ``limits``; the live count,
      in ``usage``
  * - ``id``, ``..._id``
    - an opaque identifier, which a client MUST NOT parse, order or construct
  * - ``..._url``, ``url``
    - a link the client follows and never constructs
  * - ``type``, ``..._type``
    - an error ``type`` URI
  * - ``kind``
    - a closed set naming what an object is
  * - ``reason``
    - on an error or a stream event, a closed sub-case a client may branch on;
      on a transition or a cancel, prose
  * - ``..._reason``
    - prose, for display only
  * - ``..._cause``
    - a closed set saying why a ``..._at`` is set
  * - ``can_...``
    - a boolean about what the caller may do

* **Absent and** ``null`` **differ.** Absent means the concept does not apply to
  this deployment or object; ``null`` means it applies and the value is empty or
  unknown. A client MUST NOT conflate them.
* **A limit is a non-negative integer,** ``null`` **or absent.** ``0`` means none
  allowed, ``null`` means no ceiling, and absent means the server does not
  implement it, for which a client invents no bound. A client decodes a limit
  into a nullable type.
* **A multi-valued field is a JSON array**, or an object keyed by name. The one
  exception is ``scope``, space-delimited wherever it appears, as
  :rfc:`6749#section-3.3` defines it.

URLs the server hands over
^^^^^^^^^^^^^^^^^^^^^^^^^^

Where a client may reach something only by the server's leave, the server hands
over the URL and the API publishes no path to it. A client MUST NOT construct
one.

.. list-table::
  :header-rows: 1
  :widths: 45 55

  * - URL
    - What the client does with it
  * - the upload grant's ``url``
    - ``PUT`` the archive to it
  * - the ``303`` target of an artifact fetch
    - ``GET`` the bytes
  * - the ``303`` target of ``.../logs``
    - ``GET`` the live stream
  * - the ``url`` from ``POST /v1/auth/browser``, and ``verification_uri``
    - open it in a browser, for a person

* The first three are bearer secrets for what they name. A client MUST NOT log,
  print or store one, and on a retry or a resume asks for a fresh one rather
  than reuse it. So is a sign-in ``url`` whose ``expires_at`` is set: a client
  prints it only where no browser opened.
* Following a ``303`` from ``.../logs`` or an artifact fetch is a new request.
  It carries no ``Authorization``, no proof and no credential of the client's
  own. Any other ``303`` to the API's own origin carries ``Authorization`` and
  a proof signed for the target, so a client does not let its HTTP library
  follow redirects with the previous headers.
* A URL the server builds on its own origin names one of the deployment's
  configured public origins, never an address only a proxy can reach.

Pagination
^^^^^^^^^^

A collection takes ``?limit=`` and ``?cursor=``, and the next page is a
``Link`` header with ``rel="next"``, absent on the last page.

* A client follows ``rel="next"`` on any list response, documented as paginated
  or not, as given. It never rebuilds the request around ``cursor``, which is
  opaque and carries every filter.
* Every collection is ordered by ``created_at``, newest first, with ``id``
  compared bytewise as the tie-breaker.
* ``limit`` defaults to 50 and is clamped to an unpublished maximum, never
  refused.
* A filter repeats to OR within its key, and filters AND across keys. An
  unrecognised value of an enumerated filter is ``400``, never an empty page.
* A stale or malformed cursor is ``400 invalid-cursor``, on which a client
  starts the listing again.

Idempotency
^^^^^^^^^^^

``POST /v1/jobs`` and ``POST /v1/jobs/{id}/submit`` take an ``Idempotency-Key``
header.

* A client MUST send a fresh key on each create and each submit, a resubmit
  after the job was sent back included. A request without one is accepted and
  not de-duplicated.
* A server honours a key for 24 hours, scoped to the caller, the endpoint and
  the path. A replay with the same body returns the original response, its
  status included, even once the job has moved on or been deleted.
* Only a final answer binds a key: a ``2xx``, or a refusal without
  ``Retry-After``. A refused create MAY leave its key unbound.
* A replay that arrives while the original is still being handled is
  ``409 job-state-conflict`` with ``reason: "in_progress"`` and ``Retry-After``.
* The same key with a different body is ``422 idempotency-key-reuse``.

After a timeout or a ``5xx``, every retry carries a fresh DPoP proof:

.. list-table::
  :header-rows: 1
  :widths: 50 50

  * - Call
    - A retry
  * - every ``GET``
    - is safe
  * - create and submit
    - is safe with the same ``Idempotency-Key`` and body
  * - ``upload-grant``
    - is safe: it re-issues, for the same ``size_bytes`` and ``digest``
  * - the presigned ``PUT``
    - starts the upload over, under a re-issued grant once this one can no
      longer start it
  * - cancel, both ``DELETE`` calls, ``POST /v1/auth/revoke``
    - is safe: each is idempotent
  * - ``POST /v1/auth/token``, refresh or device code
    - is safe for a few minutes, with a proof from the same key
  * - ``POST /v1/auth/token``, token exchange
    - is a new trade, and safe
  * - ``POST /v1/auth/device``
    - starts a new authorization, with a new code
  * - ``POST /v1/auth/browser``
    - is safe: each call answers a new page

Polling
^^^^^^^

The server sets the interval. A read of a job that is not terminal carries
``Retry-After``, in whole seconds and at least 1, and a client waits at least
that long before reading it again.

Headers
^^^^^^^

* **User-Agent.** A client MUST send one naming the product and its version,
  stable rather than an HTTP library's default -- ``siliconcompiler/0.38.4`` --
  so an operator can allowlist it at an edge. A server MUST NOT authorize on it.
* **Headers the API does not define.** A server ignores them and MUST NOT
  refuse a request for one. A client supports headers its operator configures
  for an access layer in front of the server, and sends them to the API's origin
  only, never to a storage, stream or browser URL on another origin. So a server
  never sends a client to another origin that requires them.
* **Caching.** A token response carries ``Cache-Control: no-store`` and
  ``Pragma: no-cache``, and every authenticated response
  ``Cache-Control: private, no-store``. ``GET /v1``, the same for every
  caller, carries ``max-age``; ``GET /v1/healthz`` carries ``no-store``.
* **Every response** carries ``X-Content-Type-Options: nosniff``.
* **Tracing.** ``traceparent`` is accepted on every request, and a refusal's
  ``trace_id`` is that trace.
* **A client sends no credential it did not put there itself**: none from
  ``~/.netrc``, a credential helper or a keychain, to the API, storage or a
  stream host.

Transport
^^^^^^^^^

A credential is an access or refresh token, a ``device_code`` or a
``user_code``.

1. A client MUST NOT send a credential over plaintext to a deployment that
   authenticates.
2. A deployment whose ``grant_types_supported`` names an authenticating grant is
   HTTPS-only. It refuses a plaintext request with ``426 insecure-transport``
   and an ``Upgrade`` header, never with a redirect, since by then the
   credential has been read.
3. A deployment that authenticates nobody MAY serve plaintext. Its tokens are
   bound to a key and are not bearer secrets, and the only bearer secrets it
   issues are its storage and stream URLs and its sign-in links.
4. A client never infers ``https`` from a port. Plaintext is only ever what a
   person typed.
5. An answer to an ``https`` request sends the client only to ``https`` URLs. A
   client never follows an ``https`` API to plain ``http``, and on
   ``insecure-transport`` stops and says the address must be ``https``.

.. _remote_api_auth:

Authentication
--------------

.. _remote_api_dpop:

Keys and proofs
^^^^^^^^^^^^^^^

Every session is bound to a P-256 key pair the client generates and keeps. The
private half never leaves the machine. Tokens are opaque to the client, their
``token_type`` is ``DPoP``, and each works only with a proof from the key it was
issued to (:rfc:`9449`). Every request after login carries both:

.. code-block:: text

  Authorization: DPoP <access token>
  DPoP: <proof>

``POST /v1/auth/device`` and ``POST /v1/auth/token`` take a proof and no
token. A proof is a compact JWS, freshly signed for each HTTP request:

.. code-block:: json

  // header: the public key travels in every proof
  {"typ": "dpop+jwt", "alg": "ES256",
   "jwk": {"kty": "EC", "crv": "P-256", "x": "l8tF...", "y": "9VE4..."}}

  // payload
  {"htm": "GET",
   "htu": "https://sc.example.com/v1/jobs/01J9...",
   "iat": 1789433600,
   "jti": "d90f...",
   "ath": "fUHy...",        // with an access token: base64url(SHA-256(token))
   "nonce": "eyJ7..."}      // where the server issued one

* **alg** is ``ES256``: `ECDSA
  <https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm>`__
  on the P-256 curve with SHA-256, as :rfc:`7518#section-3.4` defines it. It is
  the one algorithm ``v1`` allows: a server MUST accept it and a client MUST use
  it, and it is not negotiated.
* **htu** is canonical: scheme and host lowercased, a default port omitted, the
  path as sent, and no query or fragment. A server canonicalises both sides and
  compares against its configured public origins with the request's path, never
  against the ``Host`` or ``X-Forwarded-Host`` the request carries.
* **iat** is accepted within 60 seconds either way. The window is fixed by the
  API: a server that narrows it refuses a conforming client.
* **jti** is fresh on every request, retries and redirect follow-ups included.
* **The server** verifies the signature with the embedded key, checks the
  claims, refuses a replayed ``jti``, and compares the key's :rfc:`7638`
  thumbprint with the one the token, session or device code is bound to. A
  client never sends a thumbprint.
* **A refused proof says which check failed**: the URL, the time, the
  signature, the key or a replay.
* **Nonces.** A server MAY require one. Its challenge is
  ``401 dpop-nonce-required`` with ``WWW-Authenticate: DPoP
  error="use_dpop_nonce"`` and a ``DPoP-Nonce`` header, or ``400
  use_dpop_nonce`` at the two OAuth endpoints. A client retries once with the
  nonce and keeps one nonce per origin. A missing or stale nonce is never
  reported as a bad proof.
* **Clock.** A client whose proof is refused for its time compares its clock
  with the response's ``Date``, corrects later proofs by the difference where it
  is past the window, retries once, and tells its user.
* **No error invalidates the key**, a ``401`` included. A new key enrols a new
  device, so a client replaces its key only when its user asks it to.

Logging in
^^^^^^^^^^

``GET /v1``'s ``grant_types_supported`` says which login a deployment takes, and
a client chooses by it:

.. list-table::
  :header-rows: 1
  :widths: 45 55

  * - ``grant_type``
    - Used for
  * - ``urn:ietf:params:oauth:grant-type:device_code``
    - a person approving this machine in a browser (:rfc:`8628`)
  * - ``client_credentials``
    - a deployment that authenticates nobody
  * - ``urn:ietf:params:oauth:grant-type:token-exchange``
    - a CI pipeline presenting its own credential (:rfc:`8693`)
  * - ``refresh_token``
    - rotating a session the client already holds; every deployment that issues
      refresh tokens

A cached ``GET /v1`` can be stale, so a client still handles
``unsupported_grant_type`` by switching login. That answer never counts towards
a rate limit or a lockout.

**The device grant.** The client sends ``POST /v1/auth/device`` with a proof and
the scopes it wants, opens ``verification_uri`` in a browser and prints it with
``user_code`` and its key's thumbprint, then polls ``POST /v1/auth/token`` with
the ``device_code`` every ``interval`` seconds, each poll with a proof from the
same key. A person signs in to the page behind ``verification_uri`` and approves
the code there. That page is the deployment's, outside ``/v1``, and takes no
proof, but it MUST:

* attribute the approval to the person signed in to it, never to anything the
  request carries;
* show the code, the machine key's thumbprint as the server computed it,
  ``requesting_host`` as the client's own claim, the address the request came
  from, and the scope as it would be granted, and require a positive act;
* accept at most three wrong codes per approver, across codes, before a
  cooldown that does not reveal whether a code exists, and answer an unknown,
  expired, decided or used code identically;
* not approve a login that would take the account past its ``devices`` limit;
* not be cacheable, frameable or leak its URL through ``Referer``: it carries
  ``Content-Security-Policy: default-src 'self'; frame-ancestors 'none';
  form-action 'self'; base-uri 'none'``, ``Referrer-Policy: no-referrer``,
  ``Cache-Control: no-store`` and ``X-Content-Type-Options: nosniff``. So does
  every other HTML page this API sends a person to.

**A deployment that authenticates nobody** takes ``client_credentials`` with
``client_id=local:<subject>``. The subject is derived by the client from the
machine's fingerprint and the user's uid, and the user name goes as
``display_name``, for display. The server provisions an identity on first
contact, with ``issuer: "local"``, and binds it to the key that first presents
it; the same subject presented with another key is ``invalid_client``. A server
MAY turn the binding off where every client is one trust domain, such as a fleet
of containers sharing one machine id. It publishes ``identity_assurance:
"self_asserted"``. A client MUST NOT use this grant where it cannot derive a
fingerprint, and keeps the ``id`` ``GET /v1/me`` last reported for the server,
so it can tell a new identity from lost jobs.

**A CI pipeline** holds a credential minted for it, one line of the form
``<prefix>_<credential id>_<key>``: an opaque prefix, an id with no ``_``, and
the base64url DER encoding of a P-256 private key. It trades the credential at
``POST /v1/auth/token`` with an :rfc:`7523` assertion signed by that key, with a
proof from its own session key; the two keys MAY be the same. The trade returns
an access token and no refresh token, and the pipeline trades again when the
token expires.

**Refresh** rotates the pair: each refresh token is spent once and replaced.

* A refresh carries a proof from the session's key, or it is refused
  ``invalid_dpop_proof`` and revokes nothing.
* For a few minutes after a refresh token is replaced, a repeat of it with a
  valid proof is a retry, answered with the replacement already issued. Later,
  it is reuse: the session ends, ``invalid_grant`` with ``reason: "reused"``.
  The same holds for a redeemed ``device_code``. A client whose processes share
  one session refreshes once for all of them.
* A refresh always returns the session's full scope, and never widens it.

**Lifetimes are the server's**, read from every token response and never
assumed: ``expires_in`` for the access token; ``refresh_token_expires_in`` for
how long the client may be idle and resume, renewed on each rotation and never
past the session; and ``session_expires_in`` for when its user must log in
again, which never moves. On a token exchange, ``session_expires_in`` is what is
left of the CI credential.

The machine fingerprint
^^^^^^^^^^^^^^^^^^^^^^^

Where it can derive one, a client sends ``machine_id_hash``, an opaque hash of
the machine's identity, and ``machine_id_source``, one of ``linux_machine_id``,
``macos_platform_uuid``, ``windows_machine_guid`` or ``none``, at enrolment and
on every refresh. It is a label, not a credential: a refresh whose pair differs
from the device's is ``invalid_grant``, and the person logs in again. A device
enrolled with ``none`` has no change detection, and a token exchange carries no
pair.

.. _remote_api_scopes:

Scopes
^^^^^^

.. list-table::
  :header-rows: 1
  :widths: 20 80

  * - Scope
    - Permits
  * - ``jobs:read``
    - listing and reading jobs and nodes, the artifact listing, and live log
      output
  * - ``jobs:write``
    - create, ``upload-grant``, submit and cancel; carries ``jobs:read``
  * - ``jobs:delete``
    - ``DELETE /v1/jobs/{id}``; carries ``jobs:read``
  * - ``artifacts:read``
    - an artifact's bytes, every kind, an archived log included
  * - ``devices:read``
    - listing and reading the caller's devices
  * - ``devices:write``
    - revoking a device; carries ``devices:read``
  * - ``profile:read``
    - ``GET /v1/me``

* **The granted scope is the expanded set.** A request for ``jobs:write`` is
  granted, and echoed, as ``jobs:read jobs:write``. A check is set membership
  against it.
* **A session's scope is its ceiling**: the grant's default intersected with
  what was asked for. A device grant or ``client_credentials`` defaults to every
  scope. A CI credential defaults to ``jobs:read jobs:write artifacts:read
  profile:read``, with ``jobs:delete`` only where it was minted with it, and
  MUST NOT hold ``devices:read`` or ``devices:write``.
* **An unrecognised scope is dropped** and the rest granted; a request left with
  none is ``invalid_scope``. A request for more than the grant allows is
  narrowed, never refused.
* **Scope is checked first**, before the caller's access to the object and
  before any entitlement, and its refusal discloses neither:
  ``403 insufficient-scope`` with ``WWW-Authenticate: DPoP
  error="insufficient_scope", scope="<the scope needed>"``. A client fails on it
  and does not refresh.

Handling a 401
^^^^^^^^^^^^^^

Every ``401`` carries ``WWW-Authenticate`` with the ``DPoP`` scheme and an
``error=`` parameter. ``invalid_token`` covers two conditions a client must
treat oppositely, so it branches on the header and the body's ``type``
together:

.. list-table::
  :header-rows: 1
  :widths: 22 26 52

  * - ``error=``
    - ``type``
    - The client
  * - ``invalid_token``
    - ``invalid-token``
    - refreshes, then retries once
  * - ``invalid_token``
    - ``session-ended``
    - logs in again, and does not refresh. On ``reason: "reused"`` it also
      tells its user the session's credentials were used elsewhere
  * - ``use_dpop_nonce``
    - ``dpop-nonce-required``
    - retries once with the ``DPoP-Nonce`` it was sent
  * - ``invalid_dpop_proof``
    - ``invalid-dpop-proof``
    - fails, and does not refresh; refused for its time, it corrects its clock
      and retries once

.. _remote_api_device:

``POST /v1/auth/device``
^^^^^^^^^^^^^^^^^^^^^^^^

Starts a device authorization. The body is form-encoded, shown here as JSON.
The proof's key is the one the login will enrol.

.. code-block:: json

  {
    "scope": "jobs:read jobs:write jobs:delete artifacts:read devices:read devices:write profile:read",
                                            // REQUIRED. Space-separated; no default and no "*"
    "requesting_host":   "fabric-ws-3",     // OPTIONAL. The client's own name for its host
    "device_label":      "laptop",          // OPTIONAL. The name of the device it enrols
    "machine_id_hash":   "...",             // OPTIONAL. The fingerprint pair
    "machine_id_source": "linux_machine_id" // OPTIONAL. Absent reads as none
  }

**Response** ``200``:

.. code-block:: json

  {
    "device_code":               "...",              // REQUIRED
    "user_code":                 "WDJB-MJHT",        // REQUIRED. What the person types
    "verification_uri":          "https://.../device",              // REQUIRED
    "verification_uri_complete": "https://.../device?user_code=...", // OPTIONAL
    "expires_in":                600,                // REQUIRED. Seconds
    "interval":                  5                   // REQUIRED. Seconds between polls
  }

A refusal is in the OAuth shape: ``invalid_request`` for a missing or empty
``scope``; ``invalid_scope`` when no scope asked for is recognised;
``unsupported_grant_type`` where the deployment does not offer the device grant;
``use_dpop_nonce`` and ``invalid_dpop_proof``. A server MUST bound how fast
authorizations are created.

.. _remote_api_token:

``POST /v1/auth/token``
^^^^^^^^^^^^^^^^^^^^^^^

The only token endpoint; ``grant_type`` says which grant. The body is
form-encoded, and every grant takes a proof.

.. code-block:: json

  // grant_type=urn:ietf:params:oauth:grant-type:device_code
  {"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
   "device_code": "..."}                     // REQUIRED. A scope here is invalid_request

  // grant_type=refresh_token
  {"grant_type": "refresh_token",
   "refresh_token": "...",                   // REQUIRED
   "machine_id_hash": "...",                 // OPTIONAL. The fingerprint pair, as at enrolment
   "machine_id_source": "linux_machine_id"}  // OPTIONAL. A scope here is ignored

  // grant_type=client_credentials, where the deployment authenticates nobody
  {"grant_type": "client_credentials",
   "client_id": "local:<subject>",           // REQUIRED
   "machine_id_hash": "...",                 // OPTIONAL
   "machine_id_source": "linux_machine_id",  // OPTIONAL
   "display_name": "jchen",                  // OPTIONAL. For display only
   "scope": "jobs:read jobs:write"}          // OPTIONAL. Narrows the default

  // grant_type=urn:ietf:params:oauth:grant-type:token-exchange, for CI
  {"grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
   "subject_token": "<JWT>",                 // REQUIRED. The assertion, below
   "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",             // REQUIRED
   "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",  // OPTIONAL
   "scope": "jobs:read jobs:write"}          // OPTIONAL. Narrows the credential's scope

The token-exchange assertion is signed with the CI credential's key, ``ES256``,
and carries ``iss`` and ``sub`` equal to the credential id; ``aud``, one of the
deployment's public origins, compared as ``htu`` is; ``jti``; ``iat``; ``exp``,
no more than 300 seconds out; and ``cnf.jkt``, which MUST equal the thumbprint
of the request's proof (:rfc:`7800`), or the trade is ``invalid_grant``. Its
times are checked with 60 seconds of leeway. ``subject_token_type`` other than
the JWT type is ``invalid_request``, ``requested_token_type`` other than the
access-token type is ``invalid_target``, and ``actor_token``, ``audience`` or
``resource`` is ``invalid_request``.

**Response** ``200``:

.. code-block:: json

  {
    "access_token":  "...",              // REQUIRED. Opaque
    "token_type":    "DPoP",             // REQUIRED. Never Bearer
    "expires_in":    900,                // REQUIRED
    "refresh_token": "...",              // OPTIONAL. On every grant but token-exchange
    "refresh_token_expires_in": 604800,  // REQUIRED with refresh_token, else absent
    "session_expires_in":       2592000, // REQUIRED
    "scope":         "jobs:read jobs:write ...",   // REQUIRED on every grant: what was granted
    "issued_token_type": "urn:ietf:params:oauth:token-type:access_token"
                                         // REQUIRED on token-exchange, else absent
  }

A refresh token is never accepted as an access token, and one deployment's
tokens are never accepted by another. Refusals are in the OAuth shape, with
``reason`` where the row names one:

.. list-table::
  :header-rows: 1
  :widths: 26 44 30

  * - ``error``
    - When
    - The client
  * - ``authorization_pending``, ``slow_down``
    - the person has not decided yet
    - polls on at ``interval``, more slowly after ``slow_down``
  * - ``access_denied``
    - the person denied the login; with ``reason: "devices"``, it would take
      the account past its ``devices`` limit
    - stops. After ``devices``, a device must be revoked first
  * - ``expired_token``
    - the device code expired undecided
    - starts the login again
  * - ``invalid_grant``
    - an unknown or spent refresh token, a changed fingerprint, a refused
      assertion, or a session that has ended, with ``reason``: ``revoked``,
      ``reused``, ``expired`` or ``deactivated``
    - logs in again, and never retries the refresh
  * - ``invalid_client``
    - a ``client_credentials`` subject bound to another key
    - fails; an operator can release the binding
  * - ``unsupported_grant_type``
    - the grant is not offered here
    - switches login
  * - ``invalid_scope``
    - no scope asked for is recognised
    - fails
  * - ``use_dpop_nonce``
    - a nonce is required; ``DPoP-Nonce`` carries it
    - retries once with it
  * - ``invalid_dpop_proof``
    - the proof is missing, malformed, replayed or from the wrong key
    - fails, and does not refresh

A server MUST hold device-code polls to ``interval`` (``slow_down``), and MUST
bound the other grants per account and per source, counting against an account
only a request that verified as that account's. A caller is never refused
because of another account's traffic from the same address.

.. _remote_api_revoke:

``POST /v1/auth/revoke``
^^^^^^^^^^^^^^^^^^^^^^^^

Ends the session the caller presents, and nothing else. No body, ``{}``.

**Response** ``204``. Idempotent: revoking an ended session is ``204`` too. A
refusal is ``application/problem+json``.

.. _remote_api_browser:

``POST /v1/auth/browser``
^^^^^^^^^^^^^^^^^^^^^^^^^

A page for a person's browser. Every portal page a client opens comes from here;
the one exception is ``verification_uri``, which a person reaches before there
is a token to ask with. The JSON body names the page, with at most one member:

.. code-block:: json

  {"job_id": "01J9..."}       // the job's page
  {"terms_id": "gf12-nda"}    // a terms document's page, to read and decide
  {"artifact_id": "01J9..."}  // asking for an artifact's approval
  {}                          // the portal's home

**Response** ``200``, with ``Cache-Control: private, no-store``:

.. code-block:: json

  {"url":        "https://sc.example.com/portal/enter?token=...",  // REQUIRED
   "expires_at": "2026-10-01T18:04:30Z"}                         // REQUIRED, nullable

A time in ``expires_at`` makes ``url`` a single-use sign-in that lands on the
page, opened at once. ``null`` makes it the page itself, which the portal signs
a browser in to as it would any visit, and which a client may print or keep.
``url`` is on the portal's configured origin, never one taken from a request
header.

.. list-table::
  :header-rows: 1
  :widths: 10 25 65

  * - Status
    - ``type``
    - When
  * - ``400``
    - ``invalid-request``
    - more than one member, or one not defined here
  * - ``403``
    - ``not-permitted``
    - a CI session; or an artifact whose ``can_request_access`` is ``false``
  * - ``404``
    - ``not-found``
    - a job, artifact or document the caller cannot see

The server and the account
--------------------------

.. _remote_api_capabilities:

``GET /v1``
^^^^^^^^^^^

What the deployment runs and how it is used. No credential.

.. code-block:: json

  {
    "api_version": "v1",                 // REQUIRED. Changes only on a break
    "software": {                        // REQUIRED. Three buckets, each an open map
      "python": {"siliconcompiler": ["0.39.1", "0.39.0"]},  // must land in one image
      "tools":  {"openroad": ["2.0.1"]},                    // resolved per node
      "interpreter": {"python": ["3.12.4"]}                 // for nodes running the user's Python
    },
    "grant_types_supported": ["urn:ietf:params:oauth:grant-type:device_code",
                              "refresh_token"],              // REQUIRED
    "limits": {                          // REQUIRED, every member
      "max_job_nodes":              1000,
      "max_upload_bytes":           1073741824,
      "artifact_retention_seconds": 2592000,
      "pending_uploads":            null,
      "concurrent_jobs":            null,
      "concurrent_log_streams":     8,
      "max_archive_members":        100000,
      "max_archive_expanded_bytes": 10737418240,
      "max_download_bytes":         null,
      "abandon_after_seconds":      86400,
      "max_staging_seconds":        3600
    },
    "features": ["logs.stream"],         // REQUIRED. [] is legal
    "identity_assurance": "verified",    // REQUIRED. "verified" | "self_asserted"
    "terms_url": "https://...",          // OPTIONAL. The service terms, readable unauthenticated
    "notices": [                         // REQUIRED. [] is the normal answer
      {"level": "info",                  // "info" | "warning"
       "message": "Maintenance 27 Sep 02:00-06:00 UTC; submissions will queue.",
       "starts_at": "2026-09-27T02:00:00Z",   // nullable: already in effect
       "ends_at":   "2026-09-27T06:00:00Z"}   // nullable: until further notice
    ]
  }

* **software** has exactly the three buckets, each present and possibly
  ``{}``. Inside each, a name maps to a non-empty array of versions, most
  preferred first. A ``python`` key is a distribution name normalised under
  :pep:`503`, a ``tools`` key is lowercase, and ``siliconcompiler`` is required
  in ``python``. Every version listed MUST be runnable. A client SHOULD compare
  its own versions against the list before it creates a job; the server decides
  at create.
* **limits** are the deployment's defaults. A caller's effective values are in
  ``GET /v1/me``, which is what is enforced. ``null`` is allowed for
  ``max_download_bytes``, ``pending_uploads`` and ``concurrent_jobs``, and a
  numeric ``pending_uploads`` or ``concurrent_jobs`` MUST be enforced.
* **features** holds only registered strings. An absent string and an
  unrecognised one both mean *do not rely on it*, and each has a runtime
  refusal, ``501 feature-unsupported``, for a client whose copy of ``GET /v1``
  is stale:

  .. list-table::
    :header-rows: 1
    :widths: 22 78

    * - String
      - The deployment
    * - ``logs.stream``
      - serves one node's live output through ``.../logs``
    * - ``logs.stream.job``
      - also serves one stream for a whole running job; never advertised without
        ``logs.stream``
    * - ``projects``
      - groups jobs into projects: a create may name ``project``, and
        ``GET /v1/jobs`` widens to the caller's projects
    * - ``python.env``
      - installs a job's Python packages while it stages
        (:ref:`remote_api_python`)
    * - ``jobs.reuse``
      - answers a create whose ``run_hash`` matches one of the caller's own
        finished jobs with that job, ``200``, rather than a new one

* **identity_assurance** is advisory. Only ``verified`` asserts that the
  identities the deployment reports are verified; a client chooses its login by
  ``grant_types_supported``, never by this.
* **notices** are shown to a person, once per session and whenever they ask for
  the server's status; a client never branches on ``message``.

.. _remote_api_healthz:

``GET /v1/healthz``
^^^^^^^^^^^^^^^^^^^

Liveness, with no credential. ``200`` for ``pass`` and ``warn``, ``503`` for
``fail``, as ``application/health+json`` with ``Cache-Control: no-store``. The
body is ``{"status": "pass"}``, ``"warn"`` or ``"fail"``, and nothing else. A server that cannot read its
own store answers ``fail``. Downtime is announced in ``GET /v1``'s ``notices``,
not here.

.. _remote_api_me:

``GET /v1/me``
^^^^^^^^^^^^^^

Who the caller is, what they may use, and what stands in the way. It reports;
the server decides again at every gate.

.. code-block:: json

  {
    "id":     "01J9...",               // REQUIRED. A job's owner.id is this value
    "issuer": "https://idp.example.com",  // REQUIRED. "local" where nobody is authenticated
    "projects": [                      // REQUIRED. [] for none
      {"slug": "tapeout-alpha", "name": "Tapeout Alpha", "role": "owner",  // "owner" | "member"
       "archived_at": null}],          //   REQUIRED, nullable
    "authorized": {                    // OPTIONAL. Absent, never {}, where there are no grants
      "pdks": [{"name": "gf12", "expires_at": "2027-01-01T00:00:00Z",
                "blocked_by": ["gf12-nda"],     // OPTIONAL. Unaccepted agreements, by terms id
                "via": ["self", "project:tapeout-alpha"]}],
      "tools":        [],
      "libraries":    [],
      "fpgas":        [],
      "capabilities": [{"name": "python-packages", "expires_at": null, "via": ["self"]}]
    },
    "limits": {                        // REQUIRED, every member. The caller's effective values
      "max_download_bytes":         null,
      "concurrent_jobs":            null,
      "concurrent_nodes":           200,
      "pending_uploads":            null,
      "max_job_nodes":              500,
      "devices":                    10,
      "max_staging_seconds":        3600,
      "artifact_retention_seconds": 2592000
    },
    "usage": {                         // REQUIRED. Reported, not enforced, but concurrent_jobs
      "compute_seconds": {"used": 18000, "total": 972000, "limit": 360000,
                          "window": "calendar_month", "resets_at": "2026-11-01T00:00:00Z"},
      "license_seconds": {"vcs": {"used": 3600, "total": null, "limit": null,
                                  "window": "calendar_month", "resets_at": "2026-11-01T00:00:00Z"}},
      "storage_bytes":   {"used": 5368709120, "total": null, "limit": null,
                          "window": null, "resets_at": null},
      "concurrent_jobs": 0
    },
    "session": {                       // REQUIRED. The session this request was made in
      "kind": "interactive",           // "interactive" | "ci"
      "scope": "jobs:read jobs:write ...",
      "device_id": "01J9...",          // null for a CI session
      "access_expires_at":  "2026-10-27T12:15:00Z",
      "refresh_expires_at": "2026-11-03T12:00:00Z",  // null without a refresh token
      "session_expires_at": "2026-11-26T12:00:00Z"
    },
    "can_submit": false,               // REQUIRED
    "blocked_type": "https://siliconcompiler.com/server-errors/terms-not-accepted",
                                       // OPTIONAL. Only while can_submit is false
    "terms": [                         // REQUIRED. [] for none
      {"id": "gf12-nda",               // opaque; never branched on
       "title": "GF12 PDK NDA",        // display only
       "scope": {"applies_to": "resource", "resources": {"pdks": ["gf12"]}},
                                       // "service", or "resource" with resources
       "version": "2026-05-01",
       "accepted_at": null,            // nullable
       "declined_at": null,            // nullable
       "can_decide": true,             // a version is unaccepted and can be accepted now
       "upcoming": null}               // nullable: {"version", "effective_at", "accepted_at"}
    ]
  }

* **authorized** is an open map keyed by each resource kind's plural; a client
  ignores a kind it does not know. Every entry's ``via`` is non-empty, ``self``
  first, then each ``project:<slug>`` sorted by slug. ``expires_at`` is required, and
  ``null`` means never. A client MUST NOT match these names against a job's
  resources itself; create does. A capability's name is the exception: the
  three, ``python-packages``, ``python-wheels`` and ``python-sdist``, are
  registered, so a client MAY check one before create.
* **limits** shares six keys with ``GET /v1``. ``concurrent_nodes`` and
  ``devices`` are per account only. ``devices`` is enforced when a login is
  approved, and ``concurrent_nodes`` is reported only.
* **usage** is reporting, except ``concurrent_jobs``, the live count an enforced
  ``limits.concurrent_jobs`` is measured against. A metered key carries
  ``used`` (this window), ``total`` (all time, or ``null``), ``limit``,
  ``window`` and ``resets_at``.
* **can_submit** is ``false`` for exactly two causes, named by
  ``blocked_type``: an unaccepted ``service`` document
  (``terms-not-accepted``), or an account not yet provisioned to run jobs here
  (``account-not-provisioned``). Where both apply it names
  ``terms-not-accepted``.
* **terms** lists the documents that apply to the caller: the service's, and an
  agreement on each resource they hold. A client branches on
  ``scope.applies_to``, never on ``id``, and opens a document's page by asking
  ``POST /v1/auth/browser`` with its ``id``. A client never accepts a document
  on a person's behalf. An upcoming version MAY be accepted before it takes
  effect.

.. _remote_api_devices:

Devices
^^^^^^^

A device is a machine that can act as the caller: one key, enrolled by a login.

``GET /v1/devices``, ``{}``, answers ``200``:

.. code-block:: json

  {"items": [
    {"id":                "01J9...",          // REQUIRED
     "name":              "laptop",           // REQUIRED. device_label, renamed in the portal
     "current":           true,               // REQUIRED. Is this the calling device
     "machine_id_source": "linux_machine_id", // REQUIRED
     "enrolled_at":       "2026-09-01T10:00:00Z",  // REQUIRED
     "last_seen_at":      "2026-10-27T09:12:44Z"}  // REQUIRED, nullable. The last login or refresh
  ]}

``GET /v1/devices/{id}`` answers the same object. ``DELETE /v1/devices/{id}``
revokes every session of that device and answers ``204``; it is idempotent and
disturbs no other device. Either answers ``404`` for a device that is not the
caller's. A revoked device can enrol again, with the same key, as a new device
with a new ``id``; the revoked ``id`` never authenticates again and is no longer
listed.

Jobs
----

The submit sequence
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

  POST /v1/jobs                    201, created
  POST /v1/jobs/{id}/upload-grant  200, a presigned PUT; awaiting_input
  PUT  <the presigned URL>         the bytes, never through the API
  POST /v1/jobs/{id}/submit        202, staging

A client SHOULD create the job before it packs the archive, so a refusal at
create costs no packing, and packs and hashes the archive before it asks for the
grant, which binds both. A client whose grant expired asks for another on the
same job rather than creating a second one.

.. _remote_api_states:

Job states
^^^^^^^^^^

.. code-block:: text

  created -> awaiting_input -> staging -> queued -> running -+-> completed
                                                             +-> failed
                                                             +-> cancelling -> cancelled

  created, awaiting_input  -> cancelled      a cancel; nothing was running
  created, awaiting_input  -> abandoned      not submitted in time
  staging, queued          -> cancelling     a cancel
  staging                  -> rejected       refused on what the archive holds
  staging                  -> failed         staging-failed or staging-timed-out
  queued                   -> failed         run-interrupted: the scheduler lost it
  staging                  -> awaiting_input the one edge back: sources asked for

* ``completed`` is the only state that means success.
* **A client reads** ``terminal``, never the state's name, to know whether a job
  is over, and polls while it is ``false``.
* ``staging`` is where the server reads the archive, checks it, fetches what it
  supplies, builds Python environments and dispatches. ``state_reason`` names
  the phase. A staging job counts against ``concurrent_jobs``.
* ``rejected`` means refused before it ran, for something the user can change.
  ``failed`` from ``staging`` is the server's own failure (``staging-failed``)
  or the caller's ``max_staging_seconds`` (``staging-timed-out``).
* ``cancelling`` is entered by cancelling a ``staging``, ``queued`` or
  ``running`` job, and its one exit is ``cancelled``.
* ``abandoned`` is a job left unsubmitted for ``abandon_after_seconds`` after it
  entered ``created`` or ``awaiting_input``; a job holding an unexpired upload
  grant is never abandoned. It stays distinct from ``cancelled``.
* Deletion is not a state: ``deleted_at`` is set beside the state the job ended
  in.

Node states are a second closed set, each with its own ``terminal``:

.. list-table::
  :header-rows: 1
  :widths: 18 12 70

  * - State
    - Terminal
    - Meaning
  * - ``pending``
    - no
    - admitted, not dispatched
  * - ``queued``
    - no
    - with the scheduler
  * - ``preparing``
    - no
    - dispatched, and fetching what it runs in, such as an image
  * - ``running``
    - no
    -
  * - ``completed``
    - yes
    - finished
  * - ``failed``
    - yes
    - ``exit_code`` and the node's ``error`` say why
  * - ``skipped``
    - yes
    - by a condition, or a cache hit
  * - ``cancelled``
    - yes
    - the job ended before the node finished

A node turns terminal only once its artifacts are listed, never leaves a
terminal state, and a terminal job has only terminal nodes. A server maps
SiliconCompiler's own node statuses onto this set and passes none through.

.. _remote_api_create:

``POST /v1/jobs``
^^^^^^^^^^^^^^^^^

Creates a job. Send a fresh ``Idempotency-Key``. The top-level members are
authoritative; ``descriptor`` is the client's advance notice, which create
decides on and staging checks against the manifest.

.. code-block:: json

  {
    "design":   "picorv32",           // REQUIRED
    "jobname":  "run42",              // REQUIRED
    "project":  "rocket-v2",          // OPTIONAL. A project slug; absent for a personal job
    "run_hash": "sha256:9f2c...",     // OPTIONAL. For jobs.reuse; 1-128 printable ASCII
    "continues_from": [               // OPTIONAL. Nodes whose results come from an earlier job
      {"step": "place", "index": "0", "job_id": "01J8..."}],
    "python_packages": {              // OPTIONAL. What the run's Python imports
      "requirements": ["numpy==1.26.4"],
      "constraints":  ["scapy==2.5.0"]},
    "descriptor": {                   // OPTIONAL, and every member in it
      "flow":       "asicflow",       // the flowgraph's name
      "node_count": 42,               // the nodes this job runs
      "needs": ["python.env"],        // feature strings the job relies on
      "requested_versions": {         // lists of PEP 440 specifier sets; any one satisfies
        "python": {"siliconcompiler": ["==0.39.1"]},       // all by one image
        "tools":  {"openroad": [">=24.3.2011"], "yosys": []},  // per node; [] is any version
        "interpreter": {"python": ["==3.12.*"]}},          // only where a node runs the user's Python
      "sources": [                    // what the client expects the server to supply
        {"keypath": ["library", "acme_ip", "dataroot", "root"],
         "source":  "git+ssh://github.com/acme/ip.git",    // userinfo removed
         "ref":     "v1.2"},
        {"keypath": ["tool", "acme_sim", "task", "run", "dataroot", "scripts"],
         "private": true}]            // never uploaded, never asked for
    }
  }

**Response** ``201``, with ``Location: /v1/jobs/{id}``: the :ref:`job object
<remote_api_job>` in ``created``, carrying ``upload_sources`` where the server
asks the client for sources it will not fetch. Where the deployment has
``jobs.reuse`` and ``run_hash`` matches one of the caller's own unarchived,
undeleted jobs that ``completed`` (or failed with ``run-failed``) on the
server-supplied inputs a new job would get now, the answer is ``200`` with that
job, and nothing is created. A replayed create is ``201``.

* **project** is a slug of 2 to 63 characters of ``a-z``, ``0-9`` and ``-``,
  starting and ending with a letter or digit. A server without ``projects`` MUST
  refuse it, ``501 feature-unsupported``, rather than ignore it.
* **requested_versions** carries requirements, in the buckets of ``GET /v1``'s
  ``software``, normalised the same way. ``python`` names exactly:
  ``siliconcompiler``; the distribution providing each executed node's task
  class; each framework a task declares, such as cocotb; and each distribution
  whose installed-package dataroot the server supplies, or that holds a private
  dataroot. Each is pinned at the client's version, except a framework, which
  carries the range SiliconCompiler declares for it. A development version is
  sent as a prefix, ``==0.38.10.*``, which admits its pre-releases. A client
  normalises each tool's specifier to :pep:`440` and drops one it cannot. A
  server MUST NOT ignore a listed name, picks the job's image from ``python``
  alone, and among images that satisfy it, prefers the order ``software``
  publishes. Across the buckets, at most 500 names and 1,000 specifier sets,
  each at most 200 characters.
* **interpreter** is sent only for a job with a node that runs the user's own
  Python, such as a cocotb testbench: the major and minor version the client
  runs.
* **sources** names each dataroot by its keypath, either
  ``["library", <name>, "dataroot", <root>]`` or
  ``["tool", <tool>, "task", <task>, "dataroot", <root>]``; any other shape is
  ``400``. A source carrying userinfo is ``400``, naming the keypath and never
  the value. ``private`` is ``true`` for a dataroot whose resolver scheme ends
  in ``+private``.
* **needs** names a feature the job relies on; one the server does not
  advertise, or does not know, is ``501`` at create.

.. list-table::
  :header-rows: 1
  :widths: 8 26 66

  * - Status
    - ``type``
    - When
  * - ``400``
    - ``invalid-request``
    - a missing ``design`` or ``jobname``, or a member outside its grammar or
      bounds
  * - ``403``
    - ``terms-not-accepted``
    - an unaccepted service document, or agreement on a resource the job names
  * - ``403``
    - ``entitlement-denied``
    - no grant for a tool, resource or capability the job names
  * - ``403``
    - ``account-not-provisioned``
    - the account cannot run jobs here yet
  * - ``403``
    - ``not-permitted``
    - ``project`` names an archived project
  * - ``403``
    - ``node-limit-exceeded``
    - ``node_count`` over the caller's ``max_job_nodes``
  * - ``404``
    - ``not-found``
    - ``project`` names a project the caller is not in; checked first
  * - ``409``
    - ``job-state-conflict``
    - ``reason: "in_progress"``: the same key is still being handled
  * - ``422``
    - ``software-unavailable``
    - no image satisfies ``requested_versions``
  * - ``422``
    - ``resource-unavailable``
    - a private dataroot nothing can supply, or a controlled source the server
      does not hold
  * - ``422``
    - ``prior-results-unavailable``
    - a ``continues_from`` entry whose results cannot be used
  * - ``429``
    - ``limit-exceeded``
    - ``limit: "pending_uploads"``, with ``job_ids`` naming the jobs holding the
      slots, or ``limit: "concurrent_jobs"``; only where that limit is numeric
  * - ``501``
    - ``feature-unsupported``
    - ``project`` without ``projects``, or the first unadvertised string in
      ``needs``

A create never fetches anything. It looks up what the server already holds.

.. _remote_api_grant:

``POST /v1/jobs/{id}/upload-grant``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Issues, or re-issues, the grant to upload one archive.

.. code-block:: json

  {"size_bytes": 270532608,        // REQUIRED. Bound into the signature
   "digest":     "sha256:<hex>"}   // REQUIRED. The archive's SHA-256

**Response** ``200``:

.. code-block:: json

  {"method":     "PUT",
   "url":        "https://storage.example.com/...?X-Amz-Signature=...",
   "headers":    {"content-length": "270532608"},  // send exactly these
   "expires_at": "2026-09-14T16:19:05Z"}

* The first grant for an archive fixes its size and digest, and a re-issue MUST
  repeat both. A job has one archive, and one more each time it is sent back for
  sources.
* ``sha256`` is the only algorithm, always written with its prefix.
* ``max_upload_bytes`` bounds a job's archives together, and MUST NOT exceed
  what one ``PUT`` can carry: there is no multipart upload and no resume. A
  failed upload starts over.
* The grant bounds when the ``PUT`` may start, not how long its bytes are kept,
  and lives long enough to move ``max_upload_bytes``.

Refusals: ``403 not-permitted`` for a job the caller can read and does not own;
``409 job-state-conflict`` for a job not in ``created`` or ``awaiting_input``, or
a re-issue with a different size or digest; ``413 upload-too-large``, ``limit:
"max_upload_bytes"``.

.. _remote_api_submit:

``POST /v1/jobs/{id}/submit``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The job is ready to run. ``{}``, with a fresh ``Idempotency-Key``.

**Response** ``202``: the job object, in ``staging``. Submit checks the upload
against the grant's digest and nothing else of the archive; everything else is
checked while the job stages. A refusal of the request itself leaves the job in
``awaiting_input``, its upload kept, so the client can submit again:

.. list-table::
  :header-rows: 1
  :widths: 8 26 66

  * - Status
    - ``type``
    - When
  * - ``403``
    - ``not-permitted``
    - the caller does not own the job
  * - ``403``
    - ``terms-not-accepted``, ``account-not-provisioned``
    - as at create
  * - ``409``
    - ``job-state-conflict``
    - no upload, or past ``awaiting_input`` and not a replay; or
      ``reason: "in_progress"``
  * - ``422``
    - ``upload-digest-mismatch``
    - the upload does not match the grant's digest
  * - ``429``
    - ``limit-exceeded``
    - ``limit: "concurrent_jobs"``, where it is numeric

The run executes under the job's ``design`` and ``jobname``, and where and how
its nodes run is the deployment's choice. A manifest setting that would change
either, such as an incrementing job name or a scheduler queue, is overridden
rather than refused.

The archive
^^^^^^^^^^^

The upload is a gzip-compressed tar, ``application/gzip``. The first archive
holds only:

* the manifest, at the root;
* ``sc_collected_files/``, the files the client collected;
* ``sc_collected_files/python/``, one wheel per Python distribution no index can
  supply (:ref:`remote_api_python`);
* ``<step>/<index>/outputs/`` for each node the run reads and does not run.

Anything else is ``unrequested_member``. A follow-up archive holds only what the
server asked for.

**A file is uploaded or supplied by name, never found by path.** The server
MUST NOT resolve a file the client left out by looking at the same path on its
own disk, and never expands an environment variable. Each file is judged by its
own dataroot:

.. list-table::
  :header-rows: 1
  :widths: 50 50

  * - The file's dataroot
    - The file is
  * - a local path, a path rooted in an environment variable the client expands,
      or no dataroot
    - uploaded
  * - a Python package installed editable
    - uploaded
  * - a Python package installed normally, named in ``requested_versions.python``
    - supplied by the server, at that version
  * - a Python package installed normally, not named there
    - uploaded
  * - a remote source -- ``git``, ``https`` -- cached locally or not
    - supplied by source and ref, from the server's allowlist, or asked for
  * - a dataroot whose scheme ends in ``+private``, whatever else it is
    - supplied by the server from its own copy or its source, and never
      uploaded

Of those, a client uploads only values under keys some task in the flow
requires. Each node in the manifest carries the ``require`` set the client
computed for it by setting the task up, and a node the client could not set up
carries none; while any node's set is unknown, nothing is filtered. The server
reads the set from the manifest and MUST NOT run a task's setup itself.

* **Links.** A link MUST resolve inside the archive. A client stores a file
  once and points every other link at that copy.
* **No credential in a URL.** Every URL, in ``sources`` and in each dataroot's
  path in every manifest uploaded, goes with its userinfo removed and its query
  values masked. An archive carrying userinfo is ``credential``, and is not
  kept.
* **The archive's limits** are enforced on the bytes actually extracted:
  ``max_archive_members`` and ``max_archive_expanded_bytes``; only regular
  files, directories and links; no absolute path and no ``..``; and nothing
  extracted with the archive's ownership, setuid, setgid or device bits.
* **A job needs nobody at it.** A node with :keypath:`option,breakpoint` set is
  ``breakpoint``, and a node whose task opens a viewer -- an ``OpenTask``, which
  includes every ``ShowTask`` -- is ``interactive_task``. A ``ScreenshotTask``
  is allowed.
* **A node's task class** MUST be one the job's SiliconCompiler installation
  provides; one that is not is ``software-unavailable``, ``reason:
  "unknown_class"``. A runner never replaces a task class with its base class.

Staging
^^^^^^^

While a job stages, the server, in order: extracts the archive whose SHA-256 is
the grant's digest and nothing else; reads the manifest, with the
SiliconCompiler the job resolved to, in a sandbox holding no credential, no
network and no PDK data; and runs every check against what that read reports and
against the archive's bytes, never against the descriptor. What the manifest
says never widens what a job may reach or who may fetch its results.

A refusal found while staging ends the job ``rejected``, with the refusal as its
``error``:

.. list-table::
  :header-rows: 1
  :widths: 25 75

  * - Found
    - Refusal
  * - extracting
    - ``archive-rejected`` for a broken limit, a link out of the archive, no
      manifest, or a wheel breaking a wheel rule; ``upload-forbidden``,
      ``detected: "content"``
  * - reading the manifest
    - ``archive-rejected``: ``invalid_manifest``, ``breakpoint``,
      ``interactive_task``; ``declared-mismatch``, where the manifest's design,
      job name or SiliconCompiler version is not the job's;
      ``software-unavailable``, ``unknown_class``; ``resource-unresolved``
  * - checking what it read
    - ``archive-rejected``: ``credential``, ``unrequested_member``,
      ``missing_member``, ``python_package``; ``upload-forbidden``,
      ``detected: "attribution"``; ``resource-unavailable``;
      ``entitlement-denied``; ``terms-not-accepted``;
      ``prior-results-unavailable``; ``node-limit-exceeded``
  * - installing Python packages
    - ``software-unavailable``, ``reason: "uninstallable"``

The server's own failures end the job ``failed`` instead, with
``staging-failed``: an index or registry that does not answer, an image the
manifest is read in that cannot be pulled, a dispatch the scheduler refuses. So
does running past the caller's ``max_staging_seconds``, with
``staging-timed-out``.

``upload-forbidden`` is policy: the archive carries something controlled that
the caller may not upload, found by what the manifest calls it or by its bytes.
A rejected upload is otherwise kept as an ``input`` artifact, except one refused
``upload-forbidden``, ``credential``, or for carrying a private dataroot's
values.

Sources the server asks for
^^^^^^^^^^^^^^^^^^^^^^^^^^^

A server fetches only from its own allowlist, with no credential, never from a
link-local or private address, and checks every URL it contacts, each redirect,
submodule and LFS endpoint included. What it will not fetch, it asks the client
for, in ``upload_sources`` on the job object:

.. code-block:: json

  "upload_sources": [
    {"kind": "dataroot", "keypath": ["library", "lambda_io", "dataroot", "lambdapdk"]},
    {"kind": "python", "name": "cocotbext-wishbone"}]

* **At create**, a lookup answers with what the server already knows it will
  not supply, and the client puts those in the first archive.
* **While staging**, a fetch that fails for good -- refused, not found --
  sends the job back to ``awaiting_input`` naming only what failed. A transient
  failure is retried by the server, not asked for. The client asks for a grant
  for an archive of those alone, uploads it and submits again with a fresh
  ``Idempotency-Key``. The send-back is never refused for ``pending_uploads``,
  and ``abandon_after_seconds`` runs again from it.
* **A private dataroot is never asked for.** A server that cannot supply one
  refuses it at create, or rejects the job ``resource-unavailable`` while
  staging.
* **A client that cannot supply what it is asked for** cancels the job, with a
  ``reason`` naming each item and why, rather than upload part of it.

Continuing from an earlier job
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A run that starts part-way through its flow (:keypath:`option,from`) reads the
results of nodes it does not run. Each such node's results come from the upload,
as ``<step>/<index>/outputs/``, or from an earlier job named in
``continues_from``; one in neither is ``missing_member``, and one in both is
taken from the upload.

The named job MUST be the caller's own, the one that ran the node, not deleted,
with the node ``completed`` and its outputs and manifest neither deleted nor
withheld. The client takes the id from where it fetched the manifest, never
from the manifest. Create checks each entry and staging checks again; a failure
is ``prior-results-unavailable`` with ``step``, ``index``, ``job_id`` and a
``reason``: ``not_found``, ``not_owner``, ``deleted``, ``not_completed``,
``expired`` or ``withheld``. The job's ``nodes`` and artifacts cover only what it
runs.

.. _remote_api_python:

Python packages
^^^^^^^^^^^^^^^

A node that runs the user's own Python -- a cocotb testbench -- may need
packages. A deployment that installs them while a job stages advertises
``python.env``; a job that lists packages or uploads a wheel names it in
``descriptor.needs``. A job whose only Python is the user's own modules needs
neither: those travel as ordinary collected files.

* **python_packages** has ``requirements``, the distributions the run's Python
  imports, and ``constraints``, the installed versions of what they and the
  wheels depend on. Every entry is exactly ``name==version``, the name
  :pep:`503`-normalised and the version a full :pep:`440` one; each name appears
  once across both, and together they hold at most 1,000 entries and 64 KiB.
  They leave out every ``requested_versions.python`` name, the standard library,
  and every distribution sent as a wheel.
* **A wheel** goes in ``sc_collected_files/python/``, named as a wheel is, for a
  distribution installed editable, from a local path or file, or from version
  control. It is pure (``none-any``, no ``.so``, ``.pyd`` or ``.dylib``), holds
  no ``.pth``, ``sitecustomize.py``, ``usercustomize.py`` or ``<name>.data/``,
  depends on no URL, and overlaps nothing listed or in the image. Otherwise it
  is ``archive-rejected``, ``reason: "python_package"``.
* **A version no index has** sends the job back with
  ``{"kind": "python", "name": ...}``, and the client answers with a wheel at
  the listed version.
* **What a caller may do** is a capability, where the deployment grants them:
  ``python-packages`` to list packages, ``python-wheels`` to upload wheels, and
  ``python-sdist`` to have one built from source on the server. Missing, each is
  ``entitlement-denied`` with ``resource_kind: "capability"``.
* A package is installed at the version listed, or where that version does not
  install for the node's platform, the newest of its release line, recorded in
  ``resolved_versions``. The environment is on the tool's ``PYTHONPATH`` only,
  never SiliconCompiler's own.

.. _remote_api_list:

``GET /v1/jobs``
^^^^^^^^^^^^^^^^

The caller's jobs and their projects' jobs, newest first:
``{"items": [<job objects, without nodes>]}``, paginated. Every query parameter
is optional:

.. list-table::
  :header-rows: 1
  :widths: 20 80

  * - Parameter
    - Returns
  * - ``state``
    - jobs in that state
  * - ``terminal``
    - ``true``, only terminal jobs; ``false``, only the rest
  * - ``flow``, ``design``, ``jobname``
    - jobs with exactly that value
  * - ``project``
    - jobs in that project
  * - ``mine``
    - ``true``, only the caller's own; ``false``, only their projects' jobs that
      are not their own
  * - ``archived``
    - ``true``, only archived jobs. Absent or ``false``, only unarchived ones:
      the one filter whose default is not everything
  * - ``limit``, ``cursor``
    - pagination

A deleted job is in neither view.

.. _remote_api_job:

``GET /v1/jobs/{id}``
^^^^^^^^^^^^^^^^^^^^^

**Response** ``200``, and while the job is not terminal, ``Retry-After``:

.. code-block:: json

  {
    "id":       "01J9...",             // REQUIRED
    "state":    "running",             // REQUIRED
    "terminal": false,                 // REQUIRED. What a client polls on
    "transitions": [                   // REQUIRED. Every state entered, oldest first
      {"state": "created", "at": "2026-10-27T09:00:00Z"},
      {"state": "staging", "at": "2026-10-27T09:00:20Z"},
      {"state": "queued",  "at": "2026-10-27T09:01:02Z"},
      {"state": "running", "at": "2026-10-27T09:01:05Z"}],  // an entry MAY carry reason
    // "state_reason": "...",          // OPTIONAL. Display only; the phase while staging
    "design":   "picorv32",            // REQUIRED
    "jobname":  "run42",               // REQUIRED
    "flow":     "asicflow",            // OPTIONAL. null until the manifest is read
    "owner":    {"id": "01J9...", "name": "Alice"},   // REQUIRED. Compare id, never name
    "project":  null,                  // REQUIRED, nullable. null on a personal job
    "created_at":   "2026-10-27T09:00:00Z",   // REQUIRED
    "submitted_at": "2026-10-27T09:00:20Z",   // REQUIRED, nullable
    "started_at":   "2026-10-27T09:01:05Z",   // REQUIRED, nullable
    "finished_at":  null,              // REQUIRED, nullable. May stay null once terminal
    "archived_at":  null,              // REQUIRED, nullable. Set in the portal
    "deleted_at":   null,              // REQUIRED, nullable
    "deleted_reason": null,            // REQUIRED, nullable. Who deleted it, as prose
    "error":    null,                  // REQUIRED. A problem object when failed or rejected
    "nodes": [                         // REQUIRED. Omitted from GET /v1/jobs
      {"step": "place", "index": "0",
       "state": "completed", "terminal": true,
       "started_at": "2026-10-27T09:03:00Z", "finished_at": "2026-10-27T09:07:12Z",
       "exit_code": 0,                 // nullable; display only
       "error": null}],                // a problem object when the node failed
    "resolved_versions": {             // OPTIONAL. What the server picked, by bucket
      "python": {"siliconcompiler": ["0.39.1"]},
      "tools":  {"openroad": ["2.0.1"]}},
    // "upload_sources": [...],        // OPTIONAL. Only while the server is asking
    // "continues_from": [...],        // OPTIONAL. As sent at create
    "progress": {"total_count": 42, "completed_count": 17, "failed_count": 0,
                 "skipped_count": 0, "cancelled_count": 0}      // REQUIRED
  }

* **error** on a job, and on a node, is a :ref:`problem object
  <remote_api_errors>` with its type's members, and SHOULD carry ``detail``.
  ``detail`` never shows a reader tool output the log would withhold from them,
  a server path outside the job's build directory, or anything shaped like a
  credential. A failed node carries ``run-interrupted`` where the environment
  ended it (preemption, a lost compute node, an image that would not pull) and
  resubmitting unchanged may work, or ``run-failed`` where it would fail the same
  way, a time or memory limit included.
* **A job turns terminal** only once every artifact it will list is listed.
* **exit_code** is 0 to 255, a signal N reported as 128+N, and ``null`` where the
  tool never exited.
* **resolved_versions** holds exact versions, absent where nothing was resolved,
  such as a deployment running jobs on the host rather than in images.
* **upload_sources** is absent, never ``[]``, unless the server is asking.
* **nodes** and **progress** count only the nodes this job runs, and ``nodes`` is
  never emptied as artifacts expire.
* **Who may act.** Any member of the job's project reads it; only its owner, or
  an ``owner`` of its project for cancel and delete, may write to it. A job the
  caller cannot read is ``404``, never ``403``.

.. _remote_api_cancel:

``POST /v1/jobs/{id}/cancel``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Stops a job. The body is optional:

.. code-block:: json

  {"reason": "superseded by run43"}   // OPTIONAL. At most 300 characters, no control characters

**Response** ``202``: the job, now ``cancelling`` from ``staging``, ``queued``
or ``running``, or ``cancelled`` from ``created`` or ``awaiting_input``.
Idempotent: cancelling a ``cancelling`` or terminal job is ``202`` with the job
as it is. The reason is recorded on the transition and on each node it stopped,
whole. A reason too long is ``400``, never cut short. A caller that can read the
job and may not cancel it is ``403 not-permitted``.

.. _remote_api_delete:

``DELETE /v1/jobs/{id}``
^^^^^^^^^^^^^^^^^^^^^^^^

Deletes a job's data. ``{}``.

**Response** ``204``. Idempotent. The job MUST be terminal, or it is
``409 job-state-conflict``. Afterwards the job object stays readable, with
``deleted_at`` and a ``deleted_reason`` the server writes naming who acted, and
everything under it is ``404``. A replayed create or submit still answers as it
first did. A caller that can read the job and may not delete it is
``403 not-permitted``.

.. _remote_api_logs:

Live logs
---------

``GET /v1/jobs/{id}/logs``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Redirects to a live log stream, and never carries log bytes itself: a finished
node's log is its ``logs`` artifact. With ``?step=`` and ``?index=`` it is one
node's stream; with neither, the whole job's; one without the other is ``400``.

**Response** ``303`` to the stream host, or a refusal. For one node, the first
row that matches:

.. list-table::
  :header-rows: 1
  :widths: 45 55

  * - Case
    - Answer
  * - the deployment does not have ``logs.stream``
    - ``501 feature-unsupported``, ``feature: "logs.stream"``
  * - the caller lacks a grant on a resource in the job's set
    - ``403 entitlement-denied``
  * - the caller has accepted no version of an agreement on one
    - ``403 terms-not-accepted``, with ``blocked_by``
  * - terminal, with a ``logs`` artifact
    - ``303`` to a stream that sends ``end`` at once, naming the artifact
  * - terminal, with a ``logs`` artifact that is withheld
    - ``403 artifact-not-approved``
  * - terminal, with no log
    - ``404 not-found``
  * - running
    - ``303`` to the stream
  * - not started
    - ``409 not-ready``, ``artifact_kind: "logs"``, with ``Retry-After``

For the whole job: the same first three rows, then ``303`` to a stream that
ends at once where the job is terminal; ``409 not-ready`` where no node has
started; ``303`` where the deployment has ``logs.stream.job``; otherwise
``501 feature-unsupported``, ``feature: "logs.stream.job"``, on which a client
opens one stream per running node. A refusal names the broadest capability
missing.

The stream
^^^^^^^^^^

Following the ``303`` is a new request with no credential. What answers is
``text/event-stream``, or a refusal, such as ``429 limit-exceeded`` with
``limit: "concurrent_log_streams"``, since a slot is held only while a stream is
open.

.. code-block:: text

  event: log
  id: 8f3a1c04
  data: {"step":"place","index":"0","stream":"stdout","logged_at":"2026-10-27T09:04:01Z","text":"..."}

  event: node_state
  data: {"step":"place","index":"0","state":"completed","terminal":true,"artifact_id":"01J9..."}

  event: end
  data: {"reason":"terminal","artifact_id":"01J9..."}

* **id** is on ``log`` events only, opaque, and what ``Last-Event-ID`` resumes
  from. On a job stream it is job-wide, does not grow with the node count, and
  a resume never skips a ``log`` event on any node; an id the host cannot place
  restarts the stream from the beginning.
* **node_state** carries ``terminal`` and, once terminal, the node's ``logs``
  ``artifact_id``. It has no ``id``, so a resumed stream repeats it, and a
  client treats it as idempotent.
* **end.reason** is ``terminal``, the node or job is over, or ``expired``. A
  stream ends no later than the access token that obtained it; the client then
  asks ``.../logs`` again with a fresh token and sends ``Last-Event-ID`` to the
  new target. On a node's stream, ``end`` carries the ``logs`` ``artifact_id``.
* Order is kept within a node; across nodes it is arrival order. A stream sends
  a keep-alive more often than any proxy in front of it times out.
* **Log text is the job's own output.** A client strips control characters
  from it, and from every other string the server sends, before writing it to a
  terminal, keeping newline, tab and colour sequences.

A live stream is gated like the archive: the caller holds every resource in the
job's set and has accepted an agreement on each.

.. _remote_api_artifacts:

Artifacts
---------

``GET /v1/jobs/{id}/artifacts``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A job's results, filterable by ``kind``, ``step`` and ``index``, and paginated.

.. code-block:: json

  {"items": [
    {"id":             "01J9...",          // REQUIRED
     "step":           "place",            // REQUIRED. null for a job-level artifact
     "index":          "0",                // REQUIRED. null for a job-level artifact
     "kind":           "node",             // REQUIRED
     "media_type":     "application/gzip", // REQUIRED
     "size_bytes":     184320,             // REQUIRED
     "digest":         "sha256:...",       // REQUIRED
     "created_at":     "2026-10-27T09:07:12Z",  // REQUIRED
     "retained_until": "2026-11-26T09:07:12Z",  // REQUIRED, nullable. Kept at least until then
     "deleted_at":     null,               // REQUIRED, nullable. The bytes are gone
     "deleted_cause":  null,               // REQUIRED, nullable. "expired" | "removed"
     "deleted_reason": null,               // REQUIRED, nullable. Prose, where a person removed it
     "fetchable":      true,               // REQUIRED. For this caller; never cached across callers
     "access_requested_at": null,          // REQUIRED, nullable. The caller's pending request
     "blocked_by":     ["gf12-nda"],       // OPTIONAL. Unaccepted agreements, by terms id
     "can_request_access": false}          // REQUIRED. Only an approval is missing, and it can be asked for
  ]}

Every artifact is stored and served gzip-compressed. The listing carries at most
one artifact of each kind per node, and one job-level artifact of each kind,
except ``input``, one per upload. No kind is guaranteed, and a listing with only
a ``manifest``, or none, is conforming.

.. list-table::
  :header-rows: 1
  :widths: 15 85

  * - ``kind``
    - What it is
  * - ``input``
    - an archive the client uploaded, job-level, one per upload with the digest
      its grant bound; or, bound to a node, that node's ``inputs/``
  * - ``manifest``
    - the run's record: a node's, or the job's final one, job-level
  * - ``logs``
    - a node's log files, as a tar; or, job-level, SiliconCompiler's ``job.log``
  * - ``staging``
    - the server's record of staging the job, for its submitter
  * - ``diagnostics``
    - the deployment's own record, for its operators; never fetchable
  * - ``reports``
    - a node's metrics and reports, as a tar
  * - ``final``
    - a node's deliverables, as a tar
  * - ``outputs``
    - everything a node produced, as a tar
  * - ``node``
    - the whole node directory, as a tar; fetchable exactly when every artifact
      of the node it holds is
  * - ``issue``
    - an ``sc-issue`` testcase; never fetchable through the API

A tar bound to a node holds paths relative to the node's directory. It keeps a
link inside the job as a link to the file's real home, usually an upstream
node's ``outputs/``, and drops one that leaves the job, so a node's archive
resolves fully only beside the nodes it links to. A client SHOULD fetch ``node``
where it is fetchable, and the other kinds otherwise.

``fetchable: false`` says whether there is a way to yes: ``blocked_by`` means
accept those documents, ``can_request_access: true`` means ask, at the page
``POST /v1/auth/browser`` answers for the artifact, and neither means there is
none. ``deleted_cause`` says whether retention reclaimed the bytes or a person
removed them, and a client reports the two differently.

.. _remote_api_fetch:

``GET /v1/jobs/{id}/artifacts/{artifact_id}``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Response** ``303`` to a URL for the bytes, for one object and short-lived.

* A client compares what arrives with the listing's ``size_bytes`` and
  ``digest`` before it uses it, and discards it on a mismatch.
* A client extracts only inside the job's local directory: no path outside it,
  no link resolving outside it, no device or FIFO, and none of the archive's
  ownership, setuid or setgid bits. It writes nothing outside the job's
  directory whatever a listing says, and imports and runs nothing the results
  contain.
* Bytes served on the deployment's own origin never render as active content.

Where the artifact is not fetchable, the refusal follows the first condition
that holds:

.. list-table::
  :header-rows: 1
  :widths: 55 45

  * - Condition
    - Answer
  * - deleted
    - ``404``
  * - withheld; an ``issue`` or ``diagnostics``; a rejected job's ``input``
      where resources are controlled
    - ``403 artifact-not-approved``
  * - a ``node`` with a member not fetchable
    - its worst member's: withheld or deleted, then a missing grant, then an
      agreement, then an approval, then ``409 not-ready``
  * - still being described
    - ``409 not-ready``, with ``Retry-After``
  * - only an approval is missing
    - ``403 artifact-not-approved``
  * - a resource it derives from is not granted to the caller
    - ``403 entitlement-denied``, naming it
  * - an agreement on one is unaccepted
    - ``403 terms-not-accepted``, with ``blocked_by``
  * - fetchable, and over the caller's ``max_download_bytes``
    - ``403 download-too-large``; the portal is the way past it

.. _remote_api_errors:

Errors
------

Problem details
^^^^^^^^^^^^^^^

A refusal is an :rfc:`9457` body, ``application/problem+json``:

.. code-block:: json

  {
    "type":   "https://siliconcompiler.com/server-errors/entitlement-denied",
                                       // REQUIRED. What a client branches on
    "title":  "Not entitled to this resource",   // REQUIRED. Fixed per type
    "status": 403,                     // REQUIRED. Absent on a type that is never a response
    "detail": "The descriptor names a PDK this account holds no grant for.",
                                       // OPTIONAL. Names fields, never echoes values
    "instance": "/v1/jobs",            // OPTIONAL; a server SHOULD send it
    "resource_kind": "pdk",            // the type's own members
    "resource":      "gf22",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"   // OPTIONAL; a server SHOULD send it
  }

* **type is the contract.** ``title`` and ``detail`` are prose and may change.
  After ``type``, a client MAY branch on ``reason`` where the type defines one,
  and ignores a member it does not know. The ``type`` URI is the same on every
  deployment; each dereferences to a page documenting it.
* **A refusal is retried by waiting only where it carries** ``Retry-After``.
* **Not every failure is typed.** A proxy or the framework can answer first, and
  ``400``, ``405``, ``415`` and ``406`` MAY arrive without a problem body. A
  client reads ``Content-Type``, treats any other non-2xx as an untyped failure
  of its status class, and never assumes ``type`` exists. A ``5xx`` need not be
  typed; a client honours its ``Retry-After``.
* **A resource the caller cannot read is** ``404``, never ``403``, so a refusal
  confirms nothing. A write on a job the caller can read and may not act on is
  ``403 not-permitted``.
* A deployment that serves the type pages itself MAY say where, with
  ``Link: </server-errors/not-found>; rel="help"``.

``POST /v1/auth/device`` and ``POST /v1/auth/token`` answer what their OAuth
processing refuses in the OAuth shape, :rfc:`6749#section-5.2`:
``{"error", "error_description"}``, with ``reason`` where one applies. Their
transport refusals -- ``426 insecure-transport``, ``429 rate-limited``, ``415``
and ``405`` -- are problem bodies, as everywhere. A client at those two reads
``Content-Type`` first.

The registry
^^^^^^^^^^^^

Every ``type`` is ``https://siliconcompiler.com/server-errors/<slug>``. The
registry is closed: a server returns no other. A type with no status is never an
HTTP response, only the ``type`` of a job's or node's ``error``. The members
listed are required on that type.

.. server-errors::

Four slugs are retired and never reused: ``unsatisfiable-request``,
``version-skew``, ``too-many-attempts`` and ``scheduler-lost``.

Some types carry a ``reason``:

* ``archive-rejected``: ``member_count``, ``expanded_bytes``, ``ratio``,
  ``link_member``, ``device_member``, ``traversal``, ``missing_manifest``,
  ``invalid_manifest``, ``credential``, ``unrequested_member``,
  ``missing_member``, ``python_package``, ``breakpoint``, ``interactive_task``
  and ``extension``, for a member extension the deployment does not admit.
* ``session-ended``: ``revoked``, ``reused``, ``deactivated`` or ``expired``.
* ``software-unavailable``: ``unavailable``; ``combination``, where each python
  requirement resolves alone and no image holds them together;
  ``uninstallable``; ``unknown_class``. Its ``unresolved`` lists
  ``{"kind", "name", "requirement", "available"}``, ``kind`` being ``python``,
  ``tools``, ``interpreter``, ``class`` or ``package``, and ``available`` the
  versions a live image holds.
* ``prior-results-unavailable``: as in `Continuing from an earlier job`_.
* ``job-state-conflict``: ``in_progress``.

``limit`` on ``limit-exceeded`` names a published key: ``pending_uploads``,
``concurrent_jobs`` and ``concurrent_log_streams`` today, and ``usage``'s
``compute_seconds``, ``storage_bytes`` and ``license_seconds``, registered and
not yet raised. ``rate-limited`` is a deployment's own request rate, not a
published limit. ``resource_kind`` is ``pdk``, ``tool``, ``library``, ``fpga``
or ``capability``.

The bundled server
------------------

``python3 -m siliconcompiler.remote.server`` (:ref:`custom-servers`) implements
enough of this API to test the client against and to run jobs on one machine or
a small Slurm cluster. It authenticates nobody: it offers ``client_credentials``
and ``refresh_token``, publishes ``identity_assurance: "self_asserted"``, and
binds each local subject to its first key. Of the features it serves
``logs.stream``. It does not offer the device grant, projects, terms,
entitlements or approvals, ``python.env``, job reuse or ``continues_from``, and
it serves the error type pages at ``/server-errors/``.
