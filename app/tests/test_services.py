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


SOURCE: str = 'Source Mode'
DESTINATION: str = 'Destination Name'
PORT: str = 'Ports Role'
CONSUMER: str = 'Consumer Mode'
PROVIDER: str = 'Provider Name'
SERVICES: str = 'Services Role'

@pytest.fixture
def sample_guideline_df() -> DataFrame:
    return pd.DataFrame({
        'Id': [1],
        'Name': ['John'],
        SOURCE: ['Direct'],
        DESTINATION: ['Location'],
        PORT: [8080]
    })


@pytest.fixture
def sample_input_df() -> DataFrame:
    return pd.DataFrame({
        'ID': [1],
        'name': ['John'],
        CONSUMER: ['Direct'],
        PROVIDER: ['Location'],
        SERVICES: [8080]
    })


class TestMergeService:
    @pytest.mark.parametrize("guideline_data,input_data,expected_matched,expected_missing,expected_extra", [
        (
            {SOURCE: ["v1"], DESTINATION: ["v2"]},
            {CONSUMER: ["v1"], PROVIDER: ["v2"]},
            [SOURCE, DESTINATION],
            [],
            []
        ),
        (
            {"Id": [1], "Extra": ["data"]},
            {"Id": [1]},
            ["Id"],
            ["Extra"],
            []
        ),
        (
            {"Name": ["John"], "Age": [30]},
            {"NAME": ["John"], "AGE": [30], "Extra": ["data"]},
            ["Name", "Age"],
            [],
            ["Extra"]
        )
    ])
    def test_header_comparisons(self, guideline_data, input_data, expected_matched, expected_missing, expected_extra):
        guideline_df = pd.DataFrame(guideline_data)
        input_df = pd.DataFrame(input_data)

        result = MergeService.compare_headers(guideline_df, input_df)

        assert sorted(result[HEADERS_MATCHED]) == sorted(expected_matched)
        assert sorted(result[HEADERS_MISSING]) == sorted(expected_missing)
        assert sorted(result[HEADERS_EXTRA]) == sorted(expected_extra)

    @pytest.mark.parametrize("guideline_data,input_data,expected_result", [
        (
            {"Id": [1], "Name": ["John"]},
            {"Id": [1], "Name": ["John"]},
            {"Id": [1], "Name": ["John"]}
        ),
        (
            {SOURCE: [1], "Extra": [2]},
            {CONSUMER: [1]},
            {SOURCE: [1], "Extra": [None]}
        ),
        (
            {"A": [1], "B": [2]},
            {"C": [3]},
            {"A": [None], "B": [None]}
        )
    ])
    def test_merge_files(self, tmp_path, guideline_data, input_data, expected_result):
        # Suppress pandas warnings about future behavior
        pd.set_option('future.no_silent_downcasting', True)

        guideline_path = tmp_path / GUIDELINE_FILENAME
        input_path = tmp_path / TEST_EXCEL_INPUT

        pd.DataFrame(guideline_data).to_csv(guideline_path, index=False)
        pd.DataFrame(input_data).to_excel(input_path, index=False)

        merged_content = MergeService.merge_files(guideline_path, input_path)
        result_df = pd.read_csv(StringIO(merged_content))
        expected_df = pd.DataFrame(expected_result)

        expected_df = expected_df.replace({None: np.nan}, inplace=False)

        pd.testing.assert_frame_equal(
            result_df[expected_df.columns],
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