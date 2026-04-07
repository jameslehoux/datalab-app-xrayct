"""NeXus + TIFF ingestion for the X-ray CT plugin.

The parser is *deliberately* read-only and slice-aware: it never loads a full
3D volume into memory. For NeXus this is the responsibility of `nexusformat`
(which lazily proxies HDF5 datasets); for TIFF stacks we open only the central
file in the stack.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np


def _safe_get(node, key: str, default=None):
    """Read an NX field that may or may not exist, returning ``default``.

    Beamline NeXus files at Diamond / DLS have inconsistent layouts; this
    helper insulates the parser from missing fields rather than raising.
    """
    try:
        val = node[key].nxvalue
        # nexusformat returns 0-d numpy arrays for scalars; coerce to Python.
        if isinstance(val, np.ndarray) and val.shape == ():
            return val.item()
        return val
    except Exception:
        return default


def load_nexus(path: Path) -> tuple[dict, np.ndarray | None]:
    """Extract metadata + a central 2D slice from a NeXus/HDF5 file.

    Returns a ``(meta_dict, central_slice_or_none)`` tuple. The data array is
    accessed via ``nexusformat``'s lazy proxy, so this is O(slice) regardless
    of total volume size.
    """
    import nexusformat.nexus as nx

    root = nx.nxload(str(path), mode="r")
    entries = [c for c in root.values() if isinstance(c, nx.NXentry)]
    entry = entries[0] if entries else None

    def _first(nxclass):
        if entry is None:
            return None
        try:
            return next(iter(entry.walk()), None) and next(
                (n for n in entry.walk() if getattr(n, "nxclass", None) == nxclass),
                None,
            )
        except Exception:
            return None

    instrument = _first("NXinstrument")
    detector = _first("NXdetector")
    sample = _first("NXsample")
    mono = _first("NXmonochromator")
    source = _first("NXsource")

    meta: dict = {
        "facility": _safe_get(source, "name") if source else None,
        "beamline": _safe_get(instrument, "name") if instrument else None,
        "beam_energy_kev": _safe_get(mono, "energy") if mono else None,
        "exposure_time_s": _safe_get(detector, "count_time") if detector else None,
        "sample_name": _safe_get(sample, "name") if sample else None,
        "detector": _safe_get(detector, "description") if detector else None,
    }

    # Find the data cube. Try NXdetector/data first, then walk NXdata groups
    # but ONLY accept signals that are at least 3-D — otherwise we will happily
    # grab a 1-D ion-chamber log or temperature trace and treat it as a volume.
    data_node = None
    if detector is not None and "data" in detector:
        candidate = detector["data"]
        if getattr(candidate, "shape", None) and len(candidate.shape) >= 3:
            data_node = candidate
    if data_node is None:
        try:
            import nexusformat.nexus as _nx

            for n in entry.walk():
                if isinstance(n, _nx.NXdata) and n.nxsignal is not None:
                    candidate = n.nxsignal
                    if (
                        getattr(candidate, "shape", None) is not None
                        and len(candidate.shape) >= 3
                    ):
                        data_node = candidate
                        break
        except Exception:
            data_node = None

    central: np.ndarray | None = None
    if data_node is not None and getattr(data_node, "shape", None) is not None:
        shape = tuple(int(s) for s in data_node.shape)
        meta["shape"] = shape
        meta["dtype"] = str(data_node.dtype)
        if len(shape) >= 3:
            z_mid = shape[0] // 2
            # nxvalue on a slice returns a numpy array (lazy read).
            central = np.asarray(data_node[z_mid])

    return meta, central


def load_tiff_stack(directory: Path) -> tuple[dict, np.ndarray | None]:
    """Extract metadata + central slice from a directory of TIFFs.

    Only the *middle* file in lexicographic order is opened, so this is
    constant-time regardless of stack depth.
    """
    import tifffile

    files = sorted(p for p in directory.iterdir() if p.suffix.lower() in {".tif", ".tiff"})
    if not files:
        raise FileNotFoundError(f"No TIFFs in {directory}")
    mid = files[len(files) // 2]
    with tifffile.TiffFile(mid) as tf:
        page = tf.pages[0]
        central = page.asarray()
        meta = {
            "shape": (len(files), int(page.shape[0]), int(page.shape[1])),
            "dtype": str(page.dtype),
            "n_files": len(files),
        }
        # Intentionally NOT storing tf.ome_metadata / tf.imagej_metadata: some
        # processing pipelines emit multi-megabyte OME-XML strings that would
        # bloat the Mongo document (16 MB hard cap). shape/dtype above already
        # capture what the UI needs. Re-add as a separate File asset if a
        # downstream Phase needs the raw XML.
    return meta, central


def manifest_hash(paths: list[Path]) -> str:
    """Hash a (path, size, mtime) manifest — *not* the file bytes.

    Cheap content-addressing for change detection. Crucial for caching
    HPC results in Phase 4.
    """
    h = hashlib.sha256()
    for p in sorted(paths):
        st = p.stat()
        h.update(f"{p.name}|{st.st_size}|{int(st.st_mtime)}\n".encode())
    return h.hexdigest()


def render_preview_png(slice2d: np.ndarray, out_path: Path, max_dim: int = 1024) -> Path:
    """Normalize a 2D slice to 8-bit PNG with percentile contrast stretching.

    Uses 1st/99th percentiles to suppress hot pixels and shadow noise so the
    preview is legible across very different acquisition conditions.
    """
    from PIL import Image

    arr = slice2d.astype(np.float32)
    lo, hi = np.percentile(arr, (1, 99))
    arr = np.clip((arr - lo) / max(hi - lo, 1e-9), 0, 1)
    img = Image.fromarray((arr * 255).astype(np.uint8))
    img.thumbnail((max_dim, max_dim))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path
