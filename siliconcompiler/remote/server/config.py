'''What this deployment promises, published by ``GET /v1`` and ``GET /v1/me``.'''

import sys

from siliconcompiler import __version__

__all__ = ["LIMITS", "SCOPES", "capabilities"]


# Granted to every session: this server tells its callers apart, not what they may do.
SCOPES = ("jobs:read", "jobs:write", "jobs:delete", "artifacts:read",
          "devices:read", "devices:write", "profile:read")

LIMITS = {
    "max_job_nodes": 1000,
    "max_upload_bytes": 1 << 30,
    "artifact_retention_seconds": 30 * 86400,
    "pending_uploads": 8,
    "concurrent_jobs": 4,
    "concurrent_log_streams": 8,
    "max_archive_members": 100000,
    "max_archive_expanded_bytes": 10 << 30,
    "abandon_after_seconds": 900,
}

# Registered strings only; a feature joins this tuple with the endpoint it names.
FEATURES = ("logs.stream",)


def capabilities() -> dict:
    '''The ``GET /v1`` body.'''
    return {
        "api_version": "v1",
        "software": {
            "python": {"siliconcompiler": [__version__]},
            "tools": {},
            "interpreter": {"python": ["%d.%d.%d" % sys.version_info[:3]]},
        },
        "grant_types_supported": ["client_credentials", "refresh_token"],
        "limits": LIMITS,
        "features": list(FEATURES),
        "identity_assurance": "self_asserted",
        "notices": [],
    }
