from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from national_tool_metrics.boundaries import load_admin_boundaries
from national_tool_metrics.config import default_boundary_path, load_country_config


REPO_ROOT = Path(__file__).resolve().parents[1]


class _GeometryAccessor:
    def isna(self) -> pd.Series:
        return pd.Series([False])

    @property
    def is_empty(self) -> pd.Series:
        return pd.Series([False])


class _BoundaryFrame(pd.DataFrame):
    _metadata = ["crs"]

    @property
    def _constructor(self):
        return _BoundaryFrame

    @property
    def geometry(self) -> _GeometryAccessor:
        return _GeometryAccessor()


class BoundaryTests(unittest.TestCase):
    @patch("national_tool_metrics.boundaries.gpd.read_file")
    def test_adm0_uses_iso3_when_single_boundary_omits_shape_id(
        self,
        read_file,
    ) -> None:
        boundary = _BoundaryFrame(
            {
                "shapeGroup": ["KEN"],
                "shapeName": ["Kenya"],
                "geometry": [object()],
            }
        )
        boundary.crs = "EPSG:4326"
        read_file.return_value = boundary
        config = load_country_config("KEN", repo_root=REPO_ROOT)
        config = replace(
            config,
            country=replace(config.country, admin_level="adm0"),
            boundaries=replace(
                config.boundaries,
                path=default_boundary_path(REPO_ROOT, "KEN", "adm0"),
            ),
        )

        admin_regions = load_admin_boundaries(config)

        self.assertEqual(admin_regions["adm_id"].tolist(), ["KEN"])
        self.assertEqual(admin_regions["adm_name"].tolist(), ["Kenya"])


if __name__ == "__main__":
    unittest.main()
