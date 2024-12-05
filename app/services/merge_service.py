from io import StringIO
from typing import Dict, List
import pandas as pd
import numpy as np
from pandas import DataFrame
from app.utils.constants import (
    OPENPYXL_ENGINE, HEADERS_EXTRA, HEADERS_MISSING, HEADERS_MATCHED,
    FULL_HEADER_CONVERSIONS
)


class MergeService:
    @staticmethod
    def _convert_header(header: str) -> str:
        """Convert input header to standardized format using predefined mappings."""
        if header in FULL_HEADER_CONVERSIONS:
            return FULL_HEADER_CONVERSIONS[header]

        header_lower = header.lower()
        for pattern, replacement in FULL_HEADER_CONVERSIONS.items():
            if pattern.lower() == header_lower:
                return replacement

        for pattern, replacement in FULL_HEADER_CONVERSIONS.items():
            if pattern.lower() in header_lower:
                return replacement

        return header

    @staticmethod
    def _get_automatic_mappings(input_headers: List[str], guideline_headers: List[str]) -> Dict[str, str]:
        """Get automatic header mappings based on conversion rules."""
        mappings = {}
        for input_header in input_headers:
            converted = MergeService._convert_header(input_header)
            if converted in guideline_headers:
                mappings[input_header] = converted
        return mappings

    @staticmethod
    def merge_files(guideline_path: str, input_path: str, custom_mappings: Dict[str, str] = None) -> str:
        """Merge files while preserving data types from guideline."""
        guideline_df = pd.read_csv(guideline_path)
        input_df = pd.read_excel(input_path, engine=OPENPYXL_ENGINE)

        input_df = input_df.loc[:, ~input_df.columns.duplicated(keep='first')]

        auto_mappings = MergeService._get_automatic_mappings(
            list(input_df.columns),
            list(guideline_df.columns)
        )

        all_mappings = {**auto_mappings}
        if custom_mappings:
            all_mappings.update(custom_mappings)

        rename_dict = {
            col: mapping for col, mapping in all_mappings.items()
            if col in input_df.columns
        }
        input_df = input_df.rename(columns=rename_dict)

        result_df = pd.DataFrame(index=input_df.index)
        for col in guideline_df.columns:
            if col in input_df.columns:
                try:
                    series_data = input_df[col].apply(lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x)
                    result_df[col] = series_data
                except Exception as e:
                    print(f"Error processing column {col}: {str(e)}")
                    result_df[col] = input_df[col].astype(str)
            else:
                result_df[col] = pd.NA

        output = StringIO()
        result_df.to_csv(output, index=False, na_rep='')
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def compare_headers(guideline_df: DataFrame, input_df: DataFrame) -> Dict[str, List[str]]:
        """Compare headers between guideline and input dataframes."""
        guideline_headers = set(guideline_df.columns)
        input_headers = list(input_df.columns)

        auto_mappings = MergeService._get_automatic_mappings(input_headers, list(guideline_headers))

        converted_headers = {auto_mappings.get(h, h) for h in input_headers}
        matched = guideline_headers & converted_headers

        missing = guideline_headers - converted_headers
        extra = set(h for h in input_headers if auto_mappings.get(h, h) not in guideline_headers)

        return {
            HEADERS_MATCHED: sorted(list(matched)),
            HEADERS_MISSING: sorted(list(missing)),
            HEADERS_EXTRA: sorted(list(extra))
        }