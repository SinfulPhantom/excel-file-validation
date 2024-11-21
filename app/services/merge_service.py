from io import StringIO
from typing import Dict, List, Optional, Set
import pandas as pd
from pandas import DataFrame
from app.utils.constants import (
    OPENPYXL_ENGINE, HEADERS_EXTRA, HEADERS_MISSING, HEADERS_MATCHED,
    FULL_HEADER_CONVERSIONS
)


class MergeService:
    @staticmethod
    def _convert_header(header: str, custom_mappings: Optional[Dict[str, str]] = None) -> str:
        """
        Convert input header using custom mappings first, then fall back to predefined mappings.

        Args:
            header: The header to convert
            custom_mappings: Dictionary of user-defined header mappings

        Returns:
            Converted header string
        """
        if custom_mappings and header in custom_mappings:
            return custom_mappings[header]
        return FULL_HEADER_CONVERSIONS.get(header, header)

    @staticmethod
    def merge_files(guideline_path: str, input_path: str, custom_mappings: Optional[Dict[str, str]] = None) -> str:
        """
        Merge input Excel file with guideline CSV, applying both custom and predefined header mappings.
        """
        # Load files with string dtype to prevent type conversion issues
        guideline_df: DataFrame = pd.read_csv(guideline_path, dtype=str)
        input_df: DataFrame = pd.read_excel(
            input_path,
            engine=OPENPYXL_ENGINE,
            dtype=str,
            na_filter=False  # Prevent NaN conversion
        )

        # Convert all values to strings and replace NaN
        for col in input_df.columns:
            input_df[col] = input_df[col].astype(str).replace('nan', '')

        # Create mapping for header conversions while preserving case
        header_mapping: Dict = {}
        for col in input_df.columns:
            converted: str = MergeService._convert_header(col, custom_mappings)
            if converted != col:
                matching_guideline_col = next(
                    (gcol for gcol in guideline_df.columns
                     if gcol.lower() == converted.lower()),
                    converted
                )
                header_mapping[col] = matching_guideline_col

        # Rename columns using the mapping
        if header_mapping:
            input_df = input_df.rename(columns=header_mapping)

        # Create result DataFrame with guideline columns
        result_df: DataFrame = pd.DataFrame(columns=guideline_df.columns, dtype=str)

        # Copy data for matched columns, use empty string for missing ones
        for col in guideline_df.columns:
            result_df[col] = input_df[col] if col in input_df.columns else ''

        output: StringIO = StringIO()
        result_df.to_csv(output, index=False)
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
        guideline_headers: Set = set(guideline_df.columns)
        input_headers: Set = set(input_df.columns)

        matched_headers: List = sorted(list(guideline_headers & input_headers))
        missing_headers: List = sorted(list(guideline_headers - input_headers))
        extra_headers: List = sorted(list(input_headers - guideline_headers))

        return {
            HEADERS_MATCHED: matched_headers,
            HEADERS_MISSING: missing_headers,
            HEADERS_EXTRA: extra_headers
        }