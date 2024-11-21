from io import StringIO
from typing import Dict, List
import re
import pandas as pd
from pandas import DataFrame
from app.utils.constants import (
    OPENPYXL_ENGINE, HEADERS_EXTRA, HEADERS_MISSING, HEADERS_MATCHED,
    FULL_HEADER_CONVERSIONS
)


class MergeService:
    @staticmethod
    def _convert_header(header: str) -> str:
        """
        Convert input header to standardized format using predefined mappings.

        Uses FULL_HEADER_CONVERSIONS dictionary for exact matches only. Headers
        not found in the mapping are returned unchanged.

        Args:
            header: The input header string to convert

        Returns:
            The converted header if a mapping exists, otherwise the original header
        """
        return FULL_HEADER_CONVERSIONS.get(header, header)

    @staticmethod
    def merge_files(guideline_path: str, input_path: str) -> str:
        """
        Merge input Excel file with guideline CSV based on header mappings.

        Process:
        1. Load guideline and input files
        2. Convert input headers using standardized mappings
        3. Add missing columns with NA values
        4. Reorder columns to match guideline
        5. Convert to CSV string

        Args:
            guideline_path: Path to the guideline CSV file
            input_path: Path to the input Excel file

        Returns:
            String containing merged data in CSV format
        """
        guideline_df = pd.read_csv(guideline_path)
        input_df = pd.read_excel(input_path, engine=OPENPYXL_ENGINE)

        header_mapping = {col: MergeService._convert_header(col) for col in input_df.columns}
        input_df = input_df.rename(columns=header_mapping)

        for col in guideline_df.columns:
            if col not in input_df.columns:
                input_df[col] = pd.NA

        input_df = input_df[guideline_df.columns]

        output = StringIO()
        input_df.to_csv(output, index=False)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def compare_headers(guideline_df: DataFrame, input_df: DataFrame) -> Dict[str, List[str]]:
        """
        Compare headers between guideline and input dataframes.

        Process:
        1. Convert input headers using standardized mappings
        2. Find intersections and differences between header sets:
           - Matched: Headers present in both after conversion
           - Missing: Guideline headers not in converted input
           - Extra: Input headers with no guideline match

        Args:
            guideline_df: DataFrame containing guideline data
            input_df: DataFrame containing input data

        Returns:
            Dictionary with matched, missing, and extra headers
        """
        input_converted = {col: MergeService._convert_header(col) for col in input_df.columns}

        guideline_headers = set(guideline_df.columns)
        converted_input_headers = set(input_converted.values())

        return {
            HEADERS_MATCHED: sorted(list(guideline_headers & converted_input_headers)),
            HEADERS_MISSING: sorted(list(guideline_headers - converted_input_headers)),
            HEADERS_EXTRA: sorted([col for col in input_df.columns
                                   if input_converted[col] not in guideline_headers])
        }