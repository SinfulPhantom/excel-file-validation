from io import StringIO
from typing import Dict

import pandas as pd
from pandas import DataFrame
from app.utils.constants import OPENPYXL_ENGINE, HEADERS_EXTRA, HEADERS_MISSING


class MergeService:
    @staticmethod
    def merge_files(guideline_path, input_path) -> str:
        guideline_df: DataFrame = pd.read_csv(guideline_path)
        input_df: DataFrame = pd.read_excel(input_path, engine=OPENPYXL_ENGINE)
        missing_columns: set = set(guideline_df.columns) - set(input_df.columns)

        for column in missing_columns:
            input_df[column]: DataFrame = pd.NA

        output: StringIO = StringIO()
        input_df.to_csv(output, index=False)
        output.seek(0)

        return output.getvalue()

    @staticmethod
    def compare_headers(guideline_df, input_df) -> Dict:
        guideline_headers: set = set(guideline_df.columns)
        input_headers: set = set(input_df.columns)

        return {
            HEADERS_MISSING: sorted(list(guideline_headers - input_headers)),
            HEADERS_EXTRA: sorted(list(input_headers - guideline_headers))
        }