from io import StringIO
from typing import Dict, List, Any

import pandas as pd
from pandas import DataFrame
from app.utils.constants import (
    OPENPYXL_ENGINE, HEADERS_EXTRA, HEADERS_MISSING,
    HEADERS_MATCHED, ABBREVIATIONS_MAP, HEADER_CONVERSIONS
)


class MergeService:
    @staticmethod
    def _expand_abbreviations(header: str) -> str:
        words: List[str] = header.lower().split()
        expanded: List = []
        for word in words:
            expanded.append(ABBREVIATIONS_MAP.get(word, word) if word in ABBREVIATIONS_MAP else word)
        return ' '.join(expanded)

    @staticmethod
    def _convert_header(header: str) -> str:
        # First expand abbreviations while preserving case
        expanded: str = MergeService._expand_abbreviations(header)

        # Then handle header conversions
        for old, new in HEADER_CONVERSIONS.items():
            if old.lower() in expanded.lower():
                # Replace while preserving case of the rest of the string
                expanded = expanded.lower().replace(old.lower(), new.lower())

        return expanded

    @staticmethod
    def merge_files(guideline_path: str, input_path: str) -> str:
        guideline_df: DataFrame = pd.read_csv(guideline_path)
        input_df: DataFrame = pd.read_excel(input_path, engine=OPENPYXL_ENGINE)

        header_mapping: Dict = {}
        for col in input_df.columns:
            converted: str = MergeService._convert_header(col)
            if converted.lower() != col.lower():
                matching_guideline_col = next(
                    (gcol for gcol in guideline_df.columns
                     if MergeService._convert_header(gcol).lower() == converted.lower()),
                    converted
                )
                header_mapping[col] = matching_guideline_col

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
    def compare_headers(guideline_df: DataFrame, input_df: DataFrame) -> Dict[str, List[str]]:
        guideline_map: Dict[str, Any] = {MergeService._convert_header(col).lower(): col for col in guideline_df.columns}
        input_map: Dict[str, Any] = {MergeService._convert_header(col).lower(): col for col in input_df.columns}

        guideline_headers = set(guideline_map.keys())
        input_headers = set(input_map.keys())

        return {
            HEADERS_MISSING: sorted([guideline_map[h] for h in guideline_headers - input_headers]),
            HEADERS_EXTRA: sorted([input_map[h] for h in input_headers - guideline_headers]),
            HEADERS_MATCHED: sorted([guideline_map[h] for h in guideline_headers & input_headers])
        }