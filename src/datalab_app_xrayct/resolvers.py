"""URI -> filesystem path resolution.

Phase 1 ships only the Diamond resolver as a worked example. Phase 2 will
expand this into a registry pattern with one resolver per facility.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Default Diamond mount prefix; overridable via the ``DATALAB_DIAMOND_MOUNT``
#: environment variable so the same plugin can run at DLS (``/dls``), at
#: Greenwich (e.g. ``/mnt/dls-mirror``), in CI (a tmpdir), etc.
DEFAULT_DIAMOND_MOUNT = "/dls"


def resolve_diamond(uri: str, mount_prefix: str | os.PathLike | None = None) -> Path:
    """Translate a ``diamond://<beamline>/<year>/<visit>/<rest>`` URI.

    Resolution order for the mount prefix:

    1. Explicit ``mount_prefix`` argument (highest priority — used by tests).
    2. ``DATALAB_DIAMOND_MOUNT`` environment variable.
    3. ``/dls`` (the production default at Diamond).

    Example
    -------
    >>> resolve_diamond(
    ...     "diamond://i13/2025/mg39713-1/experiment/scan_00123.nxs",
    ...     mount_prefix="/mnt/dls-mirror",
    ... )
    PosixPath('/mnt/dls-mirror/i13/data/2025/mg39713-1/experiment/scan_00123.nxs')
    """
    if not uri.startswith("diamond://"):
        raise ValueError(f"Not a diamond URI: {uri}")
    _, rest = uri.split("://", 1)
    parts = rest.split("/")
    if len(parts) < 4:
        raise ValueError(
            f"diamond URI must be diamond://<beamline>/<year>/<visit>/<rest>, got {uri}"
        )
    beamline, year, visit, *tail = parts

    prefix = Path(
        mount_prefix
        if mount_prefix is not None
        else os.environ.get("DATALAB_DIAMOND_MOUNT", DEFAULT_DIAMOND_MOUNT)
    )
    return prefix / beamline / "data" / year / visit / "/".join(tail)


def resolve(uri: str) -> Path:
    """Dispatch a URI to the right resolver based on its scheme."""
    scheme = uri.split("://", 1)[0]
    if scheme == "diamond":
        return resolve_diamond(uri)
    if scheme == "file":
        return Path(uri.removeprefix("file://"))
    raise NotImplementedError(f"No resolver registered for scheme {scheme!r}")
