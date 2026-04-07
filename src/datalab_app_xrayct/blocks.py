"""The X-ray CT DataBlock — datalab's catalog entry for a tomography dataset.

This block deliberately *does not* move bytes. It reads metadata from a NeXus
file (or, optionally, a TIFF stack directory) sitting on the Data Plane, builds
a typed Pydantic document, generates a small central-slice preview PNG, and
persists everything else as a URI for Phase 2's resolver to translate later.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pydatalab.blocks.base import DataBlock

from datalab_app_xrayct._version import __version__
from datalab_app_xrayct.models import (
    AcquisitionMetadata,
    ReconstructionMetadata,
    RemoteAsset,
    Shape3,
    StorageScheme,
    XrayCTMetadata,
)
from datalab_app_xrayct.parser import (
    load_nexus,
    load_tiff_stack,
    manifest_hash,
    render_preview_png,
)


class XrayCTBlock(DataBlock):
    version = __version__
    blocktype: str = "xrayct"
    name: str = "X-ray CT dataset"
    description: str = (
        "Catalog entry for an X-ray computed tomography dataset. Stores metadata "
        "and a remote-storage URI; the raw volume itself remains on the Data Plane."
    )
    accepted_file_extensions = (".nxs", ".h5", ".hdf5")

    @property
    def plot_functions(self):
        return (self.parse_and_catalog,)

    def parse_and_catalog(self):
        """Extract metadata and a central-slice preview from the source dataset."""
        # Reset transient state on every (re-)parse so the user doesn't see an
        # ever-growing pile of duplicate errors after clicking Reparse.
        self.data["errors"] = []

        # Lazy import: only needed when datalab actually invokes the block.
        try:
            from pydatalab.file_utils import get_file_info_by_id
        except ImportError as e:
            raise RuntimeError(
                "datalab-server must be installed to use the X-ray CT block."
            ) from e

        # 1. Resolve source. Two ingestion paths:
        #    (a) An explicit URI in self.data["uri"] — the production path.
        #        The actual bytes may or may not be reachable from the datalab
        #        server; if not, we still record the URI and skip parsing.
        #    (b) A file uploaded into datalab via file_id — the local-dev path.
        uri: str | None = self.data.get("uri")
        local_path: Path | None = None

        if uri is None and self.data.get("file_id"):
            info = get_file_info_by_id(self.data["file_id"], update_if_live=True)
            local_path = Path(info["location"])
            uri = f"file://{local_path.resolve()}"

        if uri is None:
            self.data["errors"] = ["No URI or file_id supplied to XrayCTBlock."]
            return

        scheme = StorageScheme(uri.split("://", 1)[0])

        # 2. Parse metadata if (and only if) the source is reachable locally.
        raw_meta: dict = {}
        preview_slice = None
        if local_path and local_path.exists():
            try:
                if local_path.is_dir():
                    raw_meta, preview_slice = load_tiff_stack(local_path)
                else:
                    raw_meta, preview_slice = load_nexus(local_path)
            except Exception as e:
                self.data["errors"].append(f"Parser error: {e}")

        # 3. Build the typed metadata model.
        shape_tuple = raw_meta.get("shape")
        shape3 = (
            Shape3(z=shape_tuple[0], y=shape_tuple[1], x=shape_tuple[2])
            if shape_tuple and len(shape_tuple) >= 3
            else None
        )

        meta = XrayCTMetadata(
            title=self.data.get("title") or (local_path.name if local_path else uri),
            description=self.data.get("description"),
            asset=RemoteAsset(
                uri=uri,
                scheme=scheme,
                size_bytes=(
                    local_path.stat().st_size
                    if local_path and local_path.is_file()
                    else None
                ),
                n_files=raw_meta.get("n_files"),
                content_hash=(
                    manifest_hash([local_path])
                    if local_path and local_path.is_file()
                    else None
                ),
            ),
            acquisition=AcquisitionMetadata(
                facility=raw_meta.get("facility"),
                beamline=raw_meta.get("beamline"),
                beam_energy_kev=raw_meta.get("beam_energy_kev"),
                exposure_time_s=raw_meta.get("exposure_time_s"),
                detector=raw_meta.get("detector"),
                sample_name=raw_meta.get("sample_name"),
            ),
            reconstruction=ReconstructionMetadata(
                shape=shape3,
                dtype=raw_meta.get("dtype"),
                is_reconstructed=False,
            ),
        )

        # 4. Render the preview PNG to a temp file. In production this should be
        #    promoted to a datalab File asset; for Phase 1 we keep it simple and
        #    record the path. (See README "Known limitations".)
        if preview_slice is not None:
            preview_dir = Path(tempfile.gettempdir()) / "datalab_xrayct_previews"
            out = preview_dir / f"{self.block_id}.png"
            render_preview_png(preview_slice, out)
            meta.preview_path = str(out)
            if shape_tuple:
                meta.preview_slice_index = shape_tuple[0] // 2

        # 5. Persist into the block document.
        self.data["xrayct_metadata"] = meta.model_dump(mode="json")
