from typing import Dict
import pytest
import os
import pandas as pd
from io import BytesIO
from pandas import DataFrame
from werkzeug.datastructures import FileStorage
from app.services.file_service import FileService
from app.services.merge_service import MergeService
from app.services.directory_service import DirectoryService
from app.utils.constants import (
    UPLOAD_FOLDER, TEMP_FOLDER, EXCEL_CONTENT_TYPE, TEST_FORMAT_XLSX,
    TEST_FORMAT_XLS, TEST_FORMAT_CSV, TEST_FORMAT_TXT, GUIDELINE_FILENAME,
    BASE_TEST_DATA_LOCATION, CSV_CONTENT_TYPE, OPENPYXL_ENGINE, TEST_EXCEL_INPUT,
    HEADERS_EXTRA, HEADERS_MISSING, BASE_TEST_DATA_EMAIL
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
    def test_compare_headers(self) -> None:
        guideline_df: DataFrame = pd.DataFrame(BASE_TEST_DATA_LOCATION)
        input_df: DataFrame = pd.DataFrame(BASE_TEST_DATA_EMAIL)

        result: Dict = MergeService.compare_headers(guideline_df, input_df)

        # Check both missing and extra headers
        assert sorted(result[HEADERS_MISSING]) == ['Location']
        assert sorted(result[HEADERS_EXTRA]) == ['Email']

    def test_merge_files(self) -> None:
        # Create test files with actual data
        guideline_df: DataFrame = pd.DataFrame({
            'Name': ['John'],
            'Age': [30],
            'Location': ['NY']
        })
        input_df: DataFrame = pd.DataFrame({
            'Name': ['John'],
            'Age': [30]
        })

        DirectoryService.ensure_upload_dirs()
        guideline_path: str = os.path.join(UPLOAD_FOLDER, GUIDELINE_FILENAME)
        input_path: str = os.path.join(UPLOAD_FOLDER, TEST_EXCEL_INPUT)

        # Save test files
        guideline_df.to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine=OPENPYXL_ENGINE) as writer:
            input_df.to_excel(writer, index=False)

        # Test merge operation
        merged_content: str = MergeService.merge_files(guideline_path, input_path)
        result_df: DataFrame = pd.read_csv(BytesIO(merged_content.encode()))

        # Verify results
        assert all(col in result_df.columns for col in ['Name', 'Age', 'Location'])
        assert result_df['Name'].iloc[0] == 'John'
        assert result_df['Age'].iloc[0] == 30
        assert pd.isna(result_df['Location'].iloc[0])


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
        test_files: list[str] = [
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