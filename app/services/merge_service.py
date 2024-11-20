from io import StringIO
from typing import Dict, List

import pandas as pd
from pandas import DataFrame
from app.utils.constants import OPENPYXL_ENGINE, HEADERS_EXTRA, HEADERS_MISSING, HEADER_CONVERSIONS


class MergeService:
    @staticmethod
    def merge_files(guideline_path, input_path) -> str:
        guideline_df: DataFrame = pd.read_csv(guideline_path)
        input_df: DataFrame = pd.read_excel(input_path, engine=OPENPYXL_ENGINE)

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

        # Add missing columns from guideline
        missing_columns: set = set(guideline_df.columns) - set(input_df.columns)
        for column in missing_columns:
            input_df[column] = pd.NA

        output: StringIO = StringIO()
        input_df.to_csv(output, index=False)
        output.seek(0)

        return output.getvalue()

    @staticmethod
    def _convert_header(header: str) -> str:
        """Convert header based on mapping dictionary"""
        header_lower = header.lower()
        for old, new in HEADER_CONVERSIONS.items():
            if old.lower() in header_lower:
                return header_lower.replace(old.lower(), new.lower())
        return header_lower

    @staticmethod
    def compare_headers(guideline_df: DataFrame, input_df: DataFrame) -> Dict[str, List[str]]:
        # Convert headers for comparison while keeping original cases
        guideline_map = {MergeService._convert_header(col): col for col in guideline_df.columns}
        input_map = {MergeService._convert_header(col): col for col in input_df.columns}

        # Compare converted headers
        guideline_headers = set(guideline_map.keys())
        input_headers = set(input_map.keys())

        return {
            HEADERS_MISSING: sorted([guideline_map[h] for h in guideline_headers - input_headers]),
            HEADERS_EXTRA: sorted([input_map[h] for h in input_headers - guideline_headers]),
            "matched_headers": sorted([guideline_map[h] for h in guideline_headers & input_headers])
        }