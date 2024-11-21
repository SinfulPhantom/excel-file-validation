from io import StringIO
from typing import Dict, List
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

        Args:
            header: The input header string to convert

        Returns:
            The converted header if a mapping exists, otherwise the original header
        """
        return FULL_HEADER_CONVERSIONS.get(header, header)

    @staticmethod
    def merge_files(guideline_path: str, input_path: str) -> str:
        """
        Merge input Excel file with guideline CSV, preserving guideline column order
        and excluding extra headers.

        Args:
            guideline_path: Path to the guideline CSV file
            input_path: Path to the input Excel file

        Returns:
            String containing merged data in CSV format with matching guideline structure
        """
        # Load files
        guideline_df = pd.read_csv(guideline_path)
        input_df = pd.read_excel(input_path, engine=OPENPYXL_ENGINE)

        # Create mapping for header conversions while preserving case
        header_mapping = {}
        for col in input_df.columns:
            converted = MergeService._convert_header(col)
            if converted != col.lower():
                # Find matching guideline column to preserve its case
                matching_guideline_col = next(
                    (gcol for gcol in guideline_df.columns
                     if MergeService._convert_header(gcol) == converted),
                    converted.title()
                )
                header_mapping[col] = matching_guideline_col

        # Rename columns using the mapping
        if header_mapping:
            input_df = input_df.rename(columns=header_mapping)

        # Add missing columns from guideline and fill with empty strings
        missing_columns = set(guideline_df.columns) - set(input_df.columns)
        for column in missing_columns:
            input_df[column] = ""

        # Reorder columns to match guideline
        input_df = input_df[guideline_df.columns]

        output: StringIO = StringIO()
        input_df.to_csv(output, index=False)
        output.seek(0)

        return output.getvalue()

    @staticmethod
    def compare_headers(guideline_df: DataFrame, input_df: DataFrame) -> Dict[str, List[str]]:
        """
        Compare headers between guideline and input dataframes.

        Args:
            guideline_df: DataFrame containing guideline data
            input_df: DataFrame containing input data

        Returns:
            Dictionary with matched, missing, and extra headers
        """
        input_converted = {col: MergeService._convert_header(col) for col in input_df.columns}

        guideline_headers = set(guideline_df.columns)
        converted_input_headers = set(input_converted.values())

        # Keep original order of matched headers from guideline
        matched_headers = [col for col in guideline_df.columns
                           if col in converted_input_headers]

        # Find removed columns
        original_input_headers = set(input_df.columns)
        removed_columns = [col for col in original_input_headers if input_converted[col] not in matched_headers]

        return {
            HEADERS_MATCHED: matched_headers,
            HEADERS_MISSING: sorted(list(guideline_headers - converted_input_headers)),
            HEADERS_EXTRA: sorted([col for col in input_df.columns if input_converted[col] not in guideline_headers]),
            "removed_columns": sorted(removed_columns)
        }