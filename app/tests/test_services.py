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
    def sample_data(self):
        """Fixture providing sample data for tests"""
        guideline_data = {
            "First Name": ["John"],
            "Last Name": ["Doe"],
            "Age": [30],
            "Email": ["john@example.com"]
        }
        input_data = {
            "First Name": ["Jane"],
            "Last Name": ["Smith"],
            "Phone": ["1234567890"],  # Extra header
            "Address": ["123 Main St"]  # Extra header
        }
        return guideline_data, input_data

    def test_header_conversion(self):
        """Test header conversion functionality"""
        for input_header, expected in FULL_HEADER_CONVERSIONS.items():
            assert MergeService._convert_header(input_header) == expected

    def test_column_order_preservation(self, tmp_path, sample_data):
        """Test that output file maintains guideline column order"""
        guideline_data, input_data = sample_data

        # Create test files
        guideline_path = tmp_path / GUIDELINE_FILENAME
        input_path = tmp_path / TEST_EXCEL_INPUT

        pd.DataFrame(guideline_data).to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine=OPENPYXL_ENGINE) as writer:
            pd.DataFrame(input_data).to_excel(writer, index=False)

        # Perform merge
        merged_content = MergeService.merge_files(guideline_path, input_path)
        result_df = pd.read_csv(StringIO(merged_content))

        # Verify column order matches guideline
        assert list(result_df.columns) == list(guideline_data.keys())

    def test_extra_headers_excluded(self, tmp_path, sample_data):
        """Test that extra headers are excluded from output"""
        guideline_data, input_data = sample_data

        # Create test files
        guideline_path = tmp_path / GUIDELINE_FILENAME
        input_path = tmp_path / TEST_EXCEL_INPUT

        pd.DataFrame(guideline_data).to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine=OPENPYXL_ENGINE) as writer:
            pd.DataFrame(input_data).to_excel(writer, index=False)

        merged_content = MergeService.merge_files(guideline_path, input_path)
        result_df = pd.read_csv(StringIO(merged_content))

        # Verify extra headers are not in result
        assert "Phone" not in result_df.columns
        assert "Address" not in result_df.columns

    def test_missing_headers_included(self, tmp_path, sample_data):
        """Test that missing headers are included with NA values"""
        guideline_data, input_data = sample_data

        # Create test files
        guideline_path = tmp_path / GUIDELINE_FILENAME
        input_path = tmp_path / TEST_EXCEL_INPUT

        pd.DataFrame(guideline_data).to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine=OPENPYXL_ENGINE) as writer:
            pd.DataFrame(input_data).to_excel(writer, index=False)

        merged_content = MergeService.merge_files(guideline_path, input_path)
        result_df = pd.read_csv(StringIO(merged_content))

        # Verify missing headers are present with NA values
        assert "Age" in result_df.columns
        assert "Email" in result_df.columns
        assert pd.isna(result_df["Age"].iloc[0])
        assert pd.isna(result_df["Email"].iloc[0])

    def test_header_comparison_accuracy(self, sample_data):
        """Test accuracy of header comparison functionality"""
        guideline_data, input_data = sample_data

        guideline_df = pd.DataFrame(guideline_data)
        input_df = pd.DataFrame(input_data)

        result = MergeService.compare_headers(guideline_df, input_df)

        assert sorted(result[HEADERS_MATCHED]) == ["First Name", "Last Name"]
        assert sorted(result[HEADERS_MISSING]) == ["Age", "Email"]
        assert sorted(result[HEADERS_EXTRA]) == ["Address", "Phone"]

    def test_merge_files_missing_columns(self, tmp_path):
        guideline_data = {
            "Source Application": ["app1"],
            "Source Environment": ["prod"],
            # "Destination Application": [""],  # Expecting empty string, not NaN
            # "Destination Environment": [""]
        }
        input_data = {
            "Source Application": ["app1"],
            "Source Environment": ["prod"]
        }

        guideline_path = tmp_path / "guideline.csv"
        input_path = tmp_path / "input.xlsx"

        pd.DataFrame(guideline_data).to_csv(guideline_path, index=False)
        with pd.ExcelWriter(input_path, engine='openpyxl') as writer:
            pd.DataFrame(input_data).to_excel(writer, index=False)

        merged_content = MergeService.merge_files(guideline_path, input_path)
        result_df = pd.read_csv(StringIO(merged_content))

        pd.testing.assert_frame_equal(result_df[guideline_data.keys()], pd.DataFrame(guideline_data))

    def test_compare_headers_removed_columns(self):
        guideline_df = pd.DataFrame({
            "Source Application": ["app1"],
            "Source Environment": ["prod"]
        })
        input_df = pd.DataFrame({
            "Source App Label": ["app1"],  # Changed to match conversion
            "Source Env": ["prod"]
        })

        result = MergeService.compare_headers(guideline_df, input_df)

        assert result[HEADERS_MATCHED] == ["Source Application", "Source Environment"]
        assert result[HEADERS_MISSING] == []
        assert result[HEADERS_EXTRA] == []
        assert sorted(result["removed_columns"]) == []


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