from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd


def validate_columns(
    frame: pd.DataFrame,
    required_columns: set[str],
    label: str,
) -> None:
    """Raise a useful error when required fields are absent."""
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"{label} is missing required columns: {sorted(missing_columns)}"
        )


def validate_unique(
    frame: pd.DataFrame,
    key_columns: list[str],
    label: str,
) -> None:
    """Require one row per supplied key."""
    validate_columns(frame, set(key_columns), label)
    duplicate_rows = frame.duplicated(key_columns, keep=False)
    if duplicate_rows.any():
        example = frame.loc[duplicate_rows, key_columns].head()
        raise ValueError(
            f"{label} contains duplicate key rows. Example:\n{example}"
        )


def quote_sqlite_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def read_gpkg_attributes(
    gpkg_path: Path,
    layer_name: str,
) -> pd.DataFrame:
    """Read a GeoPackage feature layer without decoding its geometry."""
    if not gpkg_path.is_file():
        raise FileNotFoundError(f"GeoPackage not found: {gpkg_path}")

    quoted_layer = quote_sqlite_identifier(layer_name)
    with sqlite3.connect(gpkg_path) as connection:
        layer_exists = connection.execute(
            """
            SELECT 1
            FROM gpkg_contents
            WHERE table_name = ?
            """,
            [layer_name],
        ).fetchone()
        if layer_exists is None:
            raise ValueError(
                f"Layer {layer_name!r} not found in GeoPackage: {gpkg_path}"
            )

        geometry_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM gpkg_geometry_columns
                WHERE table_name = ?
                """,
                [layer_name],
            )
        }
        column_info = connection.execute(
            f"PRAGMA table_info({quoted_layer})"
        ).fetchall()
        attribute_columns = [
            row[1]
            for row in column_info
            if row[1] not in geometry_columns and row[1] != "fid"
        ]
        if not attribute_columns:
            raise ValueError(
                f"Layer {layer_name!r} contains no attribute columns"
            )

        select_columns = ", ".join(
            quote_sqlite_identifier(column) for column in attribute_columns
        )
        query = f"SELECT {select_columns} FROM {quoted_layer}"
        return pd.read_sql_query(query, connection)


def read_admin_summary_csv(
    csv_path: Path,
    value_columns: list[str],
    adm_id_column: str = "adm_id",
) -> pd.DataFrame:
    """Load and validate a pre-aggregated administrative summary CSV."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Administrative summary not found: {csv_path}")

    frame = pd.read_csv(csv_path, dtype={adm_id_column: "string"})
    required_columns = {adm_id_column, *value_columns}
    validate_columns(frame, required_columns, csv_path.name)
    validate_unique(frame, [adm_id_column], csv_path.name)
    return frame[[adm_id_column, *value_columns]].copy()
