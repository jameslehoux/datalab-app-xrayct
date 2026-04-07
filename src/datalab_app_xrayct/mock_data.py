"""Generate lightweight mock NeXus / TIFF datasets for tests and dev.

Phase 1, Task 1.2 of the roadmap: produce ~10 MB dummy datasets that mimic
the NeXus structure of a Diamond i13-2 microCT acquisition so that the parser
and UI can be exercised without touching production data.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def make_mock_nexus(
    path: Path,
    shape: tuple[int, int, int] = (32, 128, 128),
    beamline: str = "i13-2",
    energy_kev: float = 53.0,
    exposure_s: float = 0.1,
    sample_name: str = "mock_battery_cathode",
) -> Path:
    """Write a small NeXus file structurally similar to a Diamond microCT scan.

    The data cube is a synthetic Shepp-Logan-ish phantom (just nested ellipses)
    so that previews look like *something* rather than noise.
    """
    import h5py

    z, y, x = shape
    yy, xx = np.mgrid[:y, :x].astype(np.float32)
    cy, cx = y / 2, x / 2
    base = ((yy - cy) ** 2 / (y * 0.4) ** 2 + (xx - cx) ** 2 / (x * 0.4) ** 2 < 1).astype(
        np.float32
    )
    inner = ((yy - cy) ** 2 / (y * 0.2) ** 2 + (xx - cx) ** 2 / (x * 0.15) ** 2 < 1).astype(
        np.float32
    )
    slice2d = base * 0.6 + inner * 0.4
    cube = np.broadcast_to(slice2d, (z, y, x)).copy()

    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        entry = f.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"

        instr = entry.create_group("instrument")
        instr.attrs["NX_class"] = "NXinstrument"
        instr.create_dataset("name", data=beamline)

        source = instr.create_group("source")
        source.attrs["NX_class"] = "NXsource"
        source.create_dataset("name", data="Diamond Light Source")

        mono = instr.create_group("monochromator")
        mono.attrs["NX_class"] = "NXmonochromator"
        mono.create_dataset("energy", data=energy_kev)

        det = instr.create_group("detector")
        det.attrs["NX_class"] = "NXdetector"
        det.create_dataset("description", data="PCO.edge 5.5 (mock)")
        det.create_dataset("count_time", data=exposure_s)
        det.create_dataset("data", data=cube, compression="gzip", compression_opts=4)

        sample = entry.create_group("sample")
        sample.attrs["NX_class"] = "NXsample"
        sample.create_dataset("name", data=sample_name)

    return path


if __name__ == "__main__":
    out = make_mock_nexus(Path("mock_i13.nxs"))
    print(f"Wrote {out} ({out.stat().st_size / 1024:.1f} KB)")
