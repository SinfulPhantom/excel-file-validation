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
    def _convert_header(header: str) -> str:
        """Convert input header to standardized format using predefined mappings."""
        # First try exact match
        if header in FULL_HEADER_CONVERSIONS:
            return FULL_HEADER_CONVERSIONS[header]

        # Then try case-insensitive match
        header_lower = header.lower()
        for pattern, replacement in FULL_HEADER_CONVERSIONS.items():
            if pattern.lower() == header_lower:
                return replacement

        # Finally try substring match
        for pattern, replacement in FULL_HEADER_CONVERSIONS.items():
            if pattern.lower() in header_lower:
                return replacement

        return header

    @staticmethod
    def _get_automatic_mappings(input_headers: List[str], guideline_headers: List[str]) -> Dict[str, str]:
        """Get automatic header mappings based on FULL_HEADER_CONVERSIONS."""
        mappings = {}
        for input_header in input_headers:
            converted = MergeService._convert_header(input_header)
            if converted in guideline_headers:
                mappings[input_header] = converted
        return mappings

    @staticmethod
    def merge_files(guideline_path: str, input_path: str, custom_mappings: Dict[str, str] = None) -> str:
        """Merge files while preserving data types from guideline."""
        # Load files with type inference
        guideline_df = pd.read_csv(guideline_path, dtype=str)
        input_df = pd.read_excel(input_path, engine=OPENPYXL_ENGINE)

        # Get automatic mappings
        auto_mappings = MergeService._get_automatic_mappings(
            list(input_df.columns),
            list(guideline_df.columns)
        )

        # Combine with custom mappings if provided
        all_mappings = {**auto_mappings}
        if custom_mappings:
            all_mappings.update(custom_mappings)

        # Apply mappings
        rename_dict = {
            col: mapping for col, mapping in all_mappings.items()
            if col in input_df.columns
        }
        input_df = input_df.rename(columns=rename_dict)

        # Create result DataFrame with guideline's dtypes
        result_df = pd.DataFrame(columns=guideline_df.columns)
        for col in guideline_df.columns:
            if col in input_df.columns:
                # Convert column to match guideline dtype
                result_df[col] = pd.Series(input_df[col], dtype=guideline_df[col].dtype)
            else:
                # Add empty column with correct dtype
                result_df[col] = pd.Series(dtype=guideline_df[col].dtype)

        # Convert to CSV while preserving leading zeros
        output = StringIO()
        result_df.to_csv(output, index=False, float_format='%.0f')
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def compare_headers(guideline_df: DataFrame, input_df: DataFrame) -> Dict[str, List[str]]:
        """Compare headers between guideline and input dataframes."""
        guideline_headers = set(guideline_df.columns)
        input_headers = list(input_df.columns)

        # Get automatic mappings
        auto_mappings = MergeService._get_automatic_mappings(input_headers, list(guideline_headers))

        # Find matched headers (both direct matches and through conversion)
        converted_headers = {auto_mappings.get(h, h) for h in input_headers}
        matched = guideline_headers & converted_headers

        # Find missing and extra headers
        missing = guideline_headers - converted_headers
        extra = set(h for h in input_headers if auto_mappings.get(h, h) not in guideline_headers)

        return {
            HEADERS_MATCHED: sorted(list(matched)),
            HEADERS_MISSING: sorted(list(missing)),
            HEADERS_EXTRA: sorted(list(extra))
        }