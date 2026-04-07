"""URI -> filesystem path resolution.

Phase 1 ships only the Diamond resolver as a worked example. Phase 2 will
expand this into a registry pattern with one resolver per facility.
"""

from __future__ import annotations

from pathlib import Path


def resolve_diamond(uri: str) -> Path:
    """Translate a ``diamond://<beamline>/<year>/<visit>/<rest>`` URI.

    Example
    -------
    >>> resolve_diamond("diamond://i13/2025/mg39713-1/experiment/scan_00123.nxs")
    PosixPath('/dls/i13/data/2025/mg39713-1/experiment/scan_00123.nxs')
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
    return Path("/dls") / beamline / "data" / year / visit / "/".join(tail)


def resolve(uri: str) -> Path:
    """Dispatch a URI to the right resolver based on its scheme."""
    scheme = uri.split("://", 1)[0]
    if scheme == "diamond":
        return resolve_diamond(uri)
    if scheme == "file":
        return Path(uri.removeprefix("file://"))
    raise NotImplementedError(f"No resolver registered for scheme {scheme!r}")
