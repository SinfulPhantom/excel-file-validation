from typing import List

import numpy as np
import pytest
import os
import pandas as pd
from io import BytesIO, StringIO

from pandas import DataFrame
from werkzeug.datastructures import FileStorage
from app.services.file_service import FileService
from app.services.merge_service import MergeService
from app.services.directory_service import DirectoryService
from app.utils.constants import (
    UPLOAD_FOLDER, TEMP_FOLDER, EXCEL_CONTENT_TYPE, TEST_FORMAT_XLSX,
    TEST_FORMAT_XLS, TEST_FORMAT_CSV, TEST_FORMAT_TXT, GUIDELINE_FILENAME,
    CSV_CONTENT_TYPE, OPENPYXL_ENGINE, TEST_EXCEL_INPUT,
    HEADERS_EXTRA, HEADERS_MISSING, HEADERS_MATCHED,
)


@pytest.fixture(autouse=True)
def setup_and_cleanup():
    # Setup
    DirectoryService.ensure_upload_dirs()
    yield
    # Cleanup
    DirectoryService.cleanup_temp_files()
    for directory in [UPLOAD_FOLDER, TEMP_FOLDER]:
        if os.path.exists(directory):
            os.rmdir(directory)


class TestFileService:
    def test_allowed_input_file(self) -> None:
        assert FileService.allowed_input_file(TEST_FORMAT_XLSX)
        assert FileService.allowed_input_file(TEST_FORMAT_XLS)
        assert not FileService.allowed_input_file(TEST_FORMAT_CSV)
        assert not FileService.allowed_input_file(TEST_FORMAT_TXT)

    def test_allowed_guideline_file(self) -> None:
        assert FileService.allowed_guideline_file(TEST_FORMAT_CSV)
        assert not FileService.allowed_guideline_file(TEST_FORMAT_XLSX)
        assert not FileService.allowed_guideline_file(TEST_FORMAT_TXT)

    def test_save_guideline_file(self) -> None:
        content: bytes = b'header1,header2\nvalue1,value2'
        file: FileStorage = FileStorage(
            stream=BytesIO(content),
            filename=TEST_FORMAT_CSV,
            content_type=CSV_CONTENT_TYPE
        )

        filepath, session_id = FileService.save_guideline_file(file)

        assert os.path.exists(filepath)
        assert session_id in filepath
        assert filepath.endswith(f'_{GUIDELINE_FILENAME}')

    def test_save_input_file(self) -> None:
        df: DataFrame = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        buffer: BytesIO = BytesIO()

        with pd.ExcelWriter(buffer, engine=OPENPYXL_ENGINE) as writer:
            df.to_excel(writer, index=False)

        buffer.seek(0)

        file: FileStorage = FileStorage(
            stream=buffer,
            filename=TEST_FORMAT_XLSX,
            content_type=EXCEL_CONTENT_TYPE
        )

        filepath, file_id = FileService.save_input_file(file)

        assert os.path.exists(filepath)
        assert file_id in filepath
        assert filepath.endswith(f'_{TEST_FORMAT_XLSX}')


class TestMergeService:
    @pytest.mark.parametrize("input_header,expected_output", [
        ("app server", "Application server"),
        ("env type", "Environment type"),
        ("loc name", "Location name"),
        ("ost version", "OperatingSystem version"),
        ("consumer system", "source system"),
        ("provider application", "destination application"),
        ("consuming", "source"),
        ("providing", "destination"),
        ("app env loc ost", "Application Environment Location OperatingSystem")
    ])
    def test_header_conversion(self, input_header, expected_output):
        assert MergeService._convert_header(input_header) == expected_output

    @pytest.mark.parametrize("input_header,expected_expanded", [
        ("app server", "Application server"),
        ("env type loc", "Environment type Location"),
        ("ost app", "OperatingSystem Application")
    ])
    def test_expand_abbreviations(self, input_header, expected_expanded):
        assert MergeService._expand_abbreviations(input_header) == expected_expanded

    @pytest.mark.parametrize("guideline_data,input_data,expected_matched,expected_missing,expected_extra", [
        (
            {"Application Server": ["v1"]},
            {"app server": ["v1"]},
            ["Application Server"],
            [],
            []
        ),
        (
            {"Environment Type": ["v1"], "Location Name": ["v2"]},
            {"env type": ["v1"], "loc name": ["v2"]},
            ["Environment Type", "Location Name"],
            [],
            []
        ),
        (
            {"Source System": ["v1"], "Destination Application": ["v2"]},
            {"Consumer System": ["v1"], "Provider Application": ["v2"]},
            ["Source System", "Destination Application"],
            [],
            []
        ),
        (
            {"Source Server": ["v1"]},
            {"Consuming Server": ["v1"]},
            ["Source Server"],
            [],
            []
        )
    ])
    def test_header_comparisons_with_conversions(self, guideline_data, input_data,
                                               expected_matched, expected_missing, expected_extra):
        guideline_df = pd.DataFrame(guideline_data)
        input_df = pd.DataFrame(input_data)

        result = MergeService.compare_headers(guideline_df, input_df)

        assert sorted(result[HEADERS_MATCHED]) == sorted(expected_matched)
        assert sorted(result[HEADERS_MISSING]) == sorted(expected_missing)
        assert sorted(result[HEADERS_EXTRA]) == sorted(expected_extra)

    def test_merge_files_with_conversions(self, tmp_path):
        guideline_data = {
            "Application Server": ["server1"],
            "Environment Type": ["prod"],
            "Source System": ["sys1"],
            "Destination Application": ["app1"]
        }
        input_data = {
            "app server": ["server1"],
            "env type": ["prod"],
            "Consumer System": ["sys1"],
            "Provider Application": ["app1"]
        }
        expected_columns = list(guideline_data.keys())

        guideline_path = tmp_path / GUIDELINE_FILENAME
        input_path = tmp_path / TEST_EXCEL_INPUT

        pd.DataFrame(guideline_data).to_csv(guideline_path, index=False)
        pd.DataFrame(input_data).to_excel(input_path, index=False)

        merged_content = MergeService.merge_files(guideline_path, input_path)
        result_df = pd.read_csv(StringIO(merged_content))

        assert all(col in result_df.columns for col in expected_columns)
        assert result_df["Application Server"].iloc[0] == "server1"
        assert result_df["Environment Type"].iloc[0] == "prod"
        assert result_df["Source System"].iloc[0] == "sys1"
        assert result_df["Destination Application"].iloc[0] == "app1"


class TestDirectoryService:
    def test_ensure_upload_dirs(self) -> None:
        for directory in [UPLOAD_FOLDER, TEMP_FOLDER]:
            if os.path.exists(directory):
                os.rmdir(directory)

        DirectoryService.ensure_upload_dirs()

        assert os.path.exists(UPLOAD_FOLDER)
        assert os.path.exists(TEMP_FOLDER)

    def test_cleanup_temp_files(self) -> None:
        # Create test files
        test_files: List[str] = [
            os.path.join(UPLOAD_FOLDER, 'test1.txt'),
            os.path.join(TEMP_FOLDER, 'test2.txt')
        ]

        for file in test_files:
            with open(file, 'w') as f:
                f.write('test')

        DirectoryService.cleanup_temp_files()

        assert all(not os.path.exists(file) for file in test_files)


if __name__ == '__main__':
    pytest.main()