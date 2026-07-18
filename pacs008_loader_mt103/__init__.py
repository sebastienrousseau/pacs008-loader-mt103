# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""SWIFT MT103 -> ISO 20022 pacs.008 loader for the pacs008 suite.

SWIFT MT103 is the legacy single customer credit transfer message that
correspondent banks have exchanged for decades and that ISO 20022
``pacs.008`` (FI-to-FI Customer Credit Transfer) replaces under the CBPR+
migration. This package bridges that gap: pass an MT103 text payload to
:func:`parse_mt103` and get back the flat record that the :mod:`pacs008`
library validates against the ``pacs.008.001.08`` schema and turns into
pacs.008 XML.
"""

from pacs008_loader_mt103.loader import parse_mt103

__version__ = "0.0.2"

__all__ = ["parse_mt103", "__version__"]
