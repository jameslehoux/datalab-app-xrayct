"""Phase 1 unit tests.

These exercise the parser, models, and resolver in isolation, using a tiny
mock NeXus file generated on the fly. They do NOT import `pydatalab` so they
run cleanly in CI without a datalab server installed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from datalab_app_xrayct import __version__
from datalab_app_xrayct.mock_data import make_mock_nexus
from datalab_app_xrayct.models import RemoteAsset, StorageScheme, XrayCTMetadata
from datalab_app_xrayct.parser import load_nexus, manifest_hash, render_preview_png
from datalab_app_xrayct.resolvers import resolve, resolve_diamond


def test_version():
    assert __version__


def test_resolve_diamond_i13_path():
    uri = "diamond://i13/2025/mg39713-1/experiment/scan_00123.nxs"
    assert resolve_diamond(uri) == Path("/dls/i13/data/2025/mg39713-1/experiment/scan_00123.nxs")


def test_resolve_diamond_explicit_prefix_overrides_default():
    uri = "diamond://i13/2025/mg39713-1/experiment/scan_00123.nxs"
    assert resolve_diamond(uri, mount_prefix="/mnt/dls-mirror") == Path(
        "/mnt/dls-mirror/i13/data/2025/mg39713-1/experiment/scan_00123.nxs"
    )


def test_resolve_diamond_env_var(monkeypatch):
    monkeypatch.setenv("DATALAB_DIAMOND_MOUNT", "/data/dls")
    assert resolve_diamond("diamond://i13/2025/mg39713-1/foo.nxs") == Path(
        "/data/dls/i13/data/2025/mg39713-1/foo.nxs"
    )


def test_resolve_dispatches_by_scheme():
    assert resolve("file:///tmp/foo.nxs") == Path("/tmp/foo.nxs")
    with pytest.raises(NotImplementedError):
        resolve("scarf://nope")


def test_remote_asset_rejects_uri_without_scheme():
    with pytest.raises(ValueError):
        RemoteAsset(uri="/dls/i13/data/foo.nxs", scheme=StorageScheme.DIAMOND)


def test_parser_extracts_expected_fields(tmp_path: Path):
    nxs = make_mock_nexus(tmp_path / "mock.nxs", shape=(16, 64, 64))
    meta, central = load_nexus(nxs)

    assert meta["beamline"] == "i13-2"
    assert meta["facility"] == "Diamond Light Source"
    assert meta["beam_energy_kev"] == pytest.approx(53.0)
    assert meta["exposure_time_s"] == pytest.approx(0.1)
    assert meta["sample_name"] == "mock_battery_cathode"
    assert meta["shape"] == (16, 64, 64)
    assert central is not None
    assert central.shape == (64, 64)


def test_preview_png_is_written_and_small(tmp_path: Path):
    nxs = make_mock_nexus(tmp_path / "mock.nxs", shape=(8, 64, 64))
    _, central = load_nexus(nxs)
    out = render_preview_png(central, tmp_path / "preview.png")
    assert out.exists()
    assert out.stat().st_size < 50_000  # comfortably under 50 KB for a 64×64 PNG


def test_manifest_hash_is_stable(tmp_path: Path):
    f = tmp_path / "x.nxs"
    f.write_bytes(b"hello world")
    assert manifest_hash([f]) == manifest_hash([f])


def test_parser_skips_1d_auxiliary_nxdata(tmp_path: Path):
    """Regression: a temperature log NXdata must not be mistaken for a volume.

    Real Diamond NeXus files routinely contain auxiliary 1D NXdata groups
    (ion chambers, ring current, sample temperature). The walker must skip
    them and only accept signals with ndim >= 3.
    """
    import h5py

    nxs = tmp_path / "with_aux.nxs"
    with h5py.File(nxs, "w") as f:
        entry = f.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"

        # 1D auxiliary log — appears FIRST in walk order
        aux = entry.create_group("temperature_log")
        aux.attrs["NX_class"] = "NXdata"
        ds = aux.create_dataset("temperature", data=np.linspace(20, 25, 100))
        aux.attrs["signal"] = "temperature"
        ds  # noqa

        # 3D real volume — appears LATER
        det = entry.create_group("instrument_data")
        det.attrs["NX_class"] = "NXdata"
        cube = np.zeros((8, 32, 32), dtype=np.float32)
        cube[:, 8:24, 8:24] = 1.0
        det.create_dataset("data", data=cube)
        det.attrs["signal"] = "data"

    meta, central = load_nexus(nxs)
    assert meta["shape"] == (8, 32, 32), "parser grabbed the 1D temperature log"
    assert central is not None and central.shape == (32, 32)


def test_full_metadata_roundtrip(tmp_path: Path):
    nxs = make_mock_nexus(tmp_path / "mock.nxs", shape=(16, 64, 64))
    raw, _ = load_nexus(nxs)
    doc = XrayCTMetadata(
        title="mock",
        asset=RemoteAsset(uri=f"file://{nxs}", scheme=StorageScheme.LOCAL),
    )
    # Pydantic model dumps to plain JSON-safe dict.
    dumped = doc.model_dump(mode="json")
    assert dumped["schema_version"] == "0.1"
    assert dumped["asset"]["scheme"] == "file"
    assert raw["beamline"] == "i13-2"
