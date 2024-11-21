from typing import List, Dict, Tuple

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
    HEADERS_EXTRA, HEADERS_MISSING, HEADERS_MATCHED, FULL_HEADER_CONVERSIONS, TEST_EXCEL_INPUT,
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
    @pytest.fixture
    def sample_data(self) -> Tuple[Dict, Dict]:
        """Fixture providing sample data for tests"""
        guideline_data: Dict[str, List[str]] = {
            "Source Application": ["app1"],
            "Destination Port": ["8080"],
            "Environment": ["prod"]
        }
        input_data: Dict[str, List[str]] = {
            "Consumer App": ["app1"],
            "Target Port": ["8080"],
            "Extra Field": ["test"]
        }
        return guideline_data, input_data

    def test_custom_mapping_conversion(self, tmp_path, sample_data):
        """Test that custom mappings are applied correctly during conversion"""
        guideline_data, input_data = sample_data

        # Ensure all data is explicitly string type
        guideline_df: DataFrame = pd.DataFrame(guideline_data, dtype=str)
        input_df: DataFrame = pd.DataFrame(input_data, dtype=str)

        custom_mappings: Dict[str, str] = {
            "Consumer App": "Source Application",
            "Target Port": "Destination Port"
        }

        guideline_path = tmp_path / "guideline.csv"
        input_path = tmp_path / "input.xlsx"

        # Save as strings
        guideline_df.to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine='openpyxl') as writer:
            input_df.to_excel(writer, index=False)

        merged_content: str = MergeService.merge_files(
            guideline_path,
            input_path,
            custom_mappings
        )
        result_df: DataFrame = pd.read_csv(StringIO(merged_content), dtype=str)  # Force string type on read

        assert str(result_df["Source Application"].iloc[0]) == "app1"
        assert str(result_df["Destination Port"].iloc[0]) == "8080"

    def test_merge_preserves_data_types(self, tmp_path):
        """Test that data types are preserved during merge"""
        guideline_data: DataFrame = pd.DataFrame({
            "ID": ["001", "002"],
            "Value": ["100.5", "200.7"]
        })
        input_data: DataFrame = pd.DataFrame({
            "ID": ["001", "002"],
            "Value": ["100.5", "200.7"]
        })

        guideline_path = tmp_path / "guideline.csv"
        input_path = tmp_path / "input.xlsx"

        # Save as strings
        guideline_data.to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine='openpyxl') as writer:
            input_data.to_excel(writer, index=False)

        merged_content: str = MergeService.merge_files(guideline_path, input_path)
        result_df: DataFrame = pd.read_csv(StringIO(merged_content), dtype=str)

        assert result_df["ID"].iloc[0] == "001"
        assert result_df["Value"].iloc[0] == "100.5"

    def test_compare_headers(self):
        """Test header comparison functionality"""
        guideline_df: DataFrame = pd.DataFrame({
            "Header1": [],
            "Header2": [],
            "Header3": []
        })
        input_df: DataFrame = pd.DataFrame({
            "Header1": [],
            "Header3": [],
            "Header4": []
        })

        result: Dict[str, List[str]] = MergeService.compare_headers(guideline_df, input_df)

        assert set(result[HEADERS_MATCHED]) == {"Header1", "Header3"}
        assert set(result[HEADERS_MISSING]) == {"Header2"}
        assert set(result[HEADERS_EXTRA]) == {"Header4"}


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