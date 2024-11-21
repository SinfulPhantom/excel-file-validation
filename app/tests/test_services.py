from typing import List

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
    CSV_CONTENT_TYPE, OPENPYXL_ENGINE,
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
        ("Source Application", "Source App Label"),
        ("Source IP Lists", "Source IPList"),
        ("Destination Application", "Destination App Label"),
        ("Total Connection Count", "Num Flows"),
        ("Unknown Header", "Unknown Header")  # Test non-matching header
    ])
    def test_header_conversion(self, input_header, expected_output):
        assert MergeService._convert_header(input_header) == expected_output

    @pytest.mark.parametrize("guideline_data,input_data,expected_matched,expected_missing,expected_extra", [
        (
            {"Source App Label": ["v1"], "Destination App Label": ["v2"]},
            {"Source Application": ["v1"], "Destination Application": ["v2"]},
            ["Source App Label", "Destination App Label"],
            [],
            []
        ),
        (
            {"Source Environment": ["v1"], "Source IPList": ["v2"]},
            {"Source Env": ["v1"], "Source IP Lists": ["v2"]},
            ["Source Environment", "Source IPList"],
            [],
            []
        ),
        (
            {"Num Flows": ["100"]},
            {"Total Connection Count": ["100"], "Extra": ["data"]},
            ["Num Flows"],
            [],
            ["Extra"]
        )
    ])
    def test_header_comparisons(self, guideline_data, input_data,
                              expected_matched, expected_missing, expected_extra):
        guideline_df = pd.DataFrame(guideline_data)
        input_df = pd.DataFrame(input_data)

        result = MergeService.compare_headers(guideline_df, input_df)

        assert sorted(result[HEADERS_MATCHED]) == sorted(expected_matched)
        assert sorted(result[HEADERS_MISSING]) == sorted(expected_missing)
        assert sorted(result[HEADERS_EXTRA]) == sorted(expected_extra)

    def test_merge_files(self, tmp_path):
        guideline_data = {
            "Source App Label": ["app1"],
            "Destination App Label": ["dest1"],
            "Num Flows": [100]
        }
        input_data = {
            "Source Application": ["app1"],
            "Destination Application": ["dest1"],
            "Total Connection Count": [100]
        }
        expected_df = pd.DataFrame(guideline_data)

        guideline_path = tmp_path / "guideline.csv"
        input_path = tmp_path / "input.xlsx"

        pd.DataFrame(guideline_data).to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine='openpyxl') as writer:
            pd.DataFrame(input_data).to_excel(writer, index=False)

        merged_content = MergeService.merge_files(guideline_path, input_path)
        result_df = pd.read_csv(StringIO(merged_content))

        pd.testing.assert_frame_equal(
            result_df,
            expected_df,
            check_dtype=False
        )


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