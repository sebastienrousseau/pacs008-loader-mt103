# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Regression tests for the PEP 561 ``py.typed`` marker.

``pacs008_loader_mt103`` is ``mypy --strict`` clean, but without the
``py.typed`` marker shipped in the distribution, downstream consumers get
none of those annotations. If the marker is ever dropped from the package,
these tests fail before a release goes out.
"""

import importlib.util
import os


def _package_dir() -> str:
    """Return the installed ``pacs008_loader_mt103`` package directory."""
    spec = importlib.util.find_spec("pacs008_loader_mt103")
    assert spec is not None and spec.origin is not None
    return os.path.dirname(spec.origin)


def test_py_typed_marker_present() -> None:
    """The ``py.typed`` marker must sit beside the package ``__init__``."""
    marker = os.path.join(_package_dir(), "py.typed")
    assert os.path.isfile(marker), (
        "pacs008_loader_mt103 declares itself typed (mypy --strict) but the "
        "PEP 561 py.typed marker is missing — downstream consumers would not "
        "see the annotations. Restore pacs008_loader_mt103/py.typed."
    )


def test_py_typed_marker_is_empty() -> None:
    """PEP 561 marks a package as typed with an empty ``py.typed`` file."""
    marker = os.path.join(_package_dir(), "py.typed")
    assert os.path.getsize(marker) == 0
