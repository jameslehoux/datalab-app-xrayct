"""Datalab plugin for X-ray CT and operando battery imaging datasets."""

from ._version import __version__

# NOTE: ``XrayCTBlock`` is not imported eagerly because it depends on
# ``pydatalab``, which is an optional runtime dependency. Import it directly
# from ``datalab_app_xrayct.blocks`` when needed.

__all__ = ("__version__",)
