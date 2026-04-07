# datalab-app-xrayct

A [datalab](https://datalab-org.io) plugin for cataloguing **X-ray computed
tomography (CT) and operando battery imaging datasets** from facilities like
Diamond Light Source.

## Why a plugin?

Tomography datasets routinely exceed 100 GB, so moving them to a web server is
infeasible. This plugin uses a **Control Plane / Data Plane** split:

- **Control Plane (datalab):** stores metadata, a small preview image, and a
  remote-storage **URI**.
- **Data Plane (HPC / deep storage):** keeps the raw NeXus / TIFF volumes
  exactly where they are.

## Phase 1 status (this release)

- ✅ NeXus / HDF5 metadata extraction (`nexusformat` + `h5py`)
- ✅ TIFF stack support (`tifffile`)
- ✅ Pydantic schema (`XrayCTMetadata`) with explicit URI scheme
- ✅ Central-slice PNG preview generation
- ✅ Diamond URI resolver (`diamond://i13/<year>/<visit>/...`)
- ✅ Mock NeXus generator for tests
- ✅ Vue 3 datacard component (`webapp/XrayCTBlock.vue`)

## Install

```bash
pip install -e ".[local]"
```

The `local` extra pulls in `datalab-server[apps]` so the block registers via
the `pydatalab.apps.plugins` entry point.

## URI scheme

Lock in early — Phase 2 depends on it:

```
diamond://<beamline>/<year>/<visit>/<rest>
# e.g. diamond://i13/2025/mg39713-1/experiment/scan_00123.nxs
#  →  /dls/i13/data/2025/mg39713-1/experiment/scan_00123.nxs
```

## Tests

```bash
pytest
```

Tests use a generated mock NeXus file (~few KB) and don't require any
production data or a running datalab server.

## Roadmap

See `docs/` for the full Phase 1 → 4 plan (URI routing, Zarr/Dask interactive
viewer, SLURM job dispatch).
