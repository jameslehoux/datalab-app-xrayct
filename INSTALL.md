# Installation

We recommend [`uv`](https://astral.sh/uv) for managing the Python environment.

## Quick start (unit tests / development)

```bash
git clone git@github.com:jameslehoux/datalab-app-xrayct
cd datalab-app-xrayct
uv sync --locked --dev
uv run pytest
```

This installs the plugin and its scientific dependencies (`nexusformat`,
`tifffile`, `pydantic` v2, etc.) but **does not** install `pydatalab`.
The unit tests do not require it.

## Running the plugin inside a live datalab server

The currently published `datalab-server` on PyPI pins `pydantic<2`, which is
incompatible with this plugin's pydantic v2 schema. Until a v2-compatible
release lands, install `pydatalab` directly from git into the same virtual
environment as the plugin:

```bash
# In the same venv where you installed datalab-app-xrayct
pip install "git+https://github.com/datalab-org/datalab.git#subdirectory=pydatalab"
pip install -e .

# (Re)start the datalab server. The "X-ray CT dataset" block should now appear
# in the "Add block" menu.
```

If you are running the datalab server somewhere the Diamond filesystem is not
mounted at `/dls` (e.g. a Greenwich box with the data mirrored elsewhere),
export the mount prefix:

```bash
export DATALAB_DIAMOND_MOUNT=/mnt/dls-mirror
```

## Development

```bash
uv run pre-commit install
```

This installs the pre-commit hooks so style checks run on every commit.
