from __future__ import annotations

import json
from typing import Any

from pandas import DataFrame

from real_agents.adapters.data_model.base import DataModel

def serialize_df(
    table_data: DataFrame,
    table_name: str,
    table_path: str,
    serialize_method: str = "tsv",
    num_visible_rows: int = 3,
    max_tokens: int = 1000,
    data_dir_splitter: str = "backend/data/",
) -> str:
    """Convert dataframe to a string representation."""
    if serialize_method == "tsv":
        # Here it means ignore the "path/to/the/data/<user_id/" part of the path
        pretty_path = "/".join(table_path.split(data_dir_splitter)[-1].strip("/").split("/")[1:])
        string = (
            "Here are table columns and the first {} rows of the table from the path {}"
            '(only a small part of the whole table) called "{}":\n'.format(num_visible_rows, pretty_path, table_name)
        )
        string += table_data.head(num_visible_rows).to_csv(sep="\t", index=False)
    else:
        raise ValueError("Unknown serialization method.")
    return string


class TableDataModel(DataModel):
    """A data model for table."""

    db_view: DataModel = None

    def set_db_view(self, db_data_model: DataModel) -> None:
        self.db_view = db_data_model

    def get_llm_side_data(self, serialize_method: str = "tsv", num_visible_rows: int = 3) -> Any:
        # Show the first few rows for observation.
        table_data = self.raw_data
        table_name = self.raw_data_name
        table_path = self.raw_data_path
        formatted_table = serialize_df(table_data, table_name, table_path, serialize_method, num_visible_rows)
        return formatted_table

    def get_human_side_data(self, mode: str = "HEAD") -> Any:
        # We support different mode for the front-end display.
        # For `HEAD` mode, we show the first few rows for observation.
        if mode == "HEAD":
            return self.raw_data.head()
        elif mode == "FULL":
            return self.raw_data
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    @staticmethod
    def to_react_table(table: DataFrame) -> str:
        columns = list(map(lambda item: {"accessorKey": item, "header": item}, table.columns.tolist()))
        # FIXME: NaN may not be handled here.
        data = table.fillna("").to_dict(orient="records")
        table = json.dumps({"columns": columns, "data": data})
        return table
