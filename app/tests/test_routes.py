from typing import Dict
import pytest
import os
import pandas as pd
from flask import Response
from pandas import DataFrame
from io import BytesIO, StringIO
from bs4 import BeautifulSoup
from app.utils.constants import (
    UPLOAD_FOLDER, TEMP_FOLDER, MAX_FILE_SIZE_BYTES,
    MSG_MISSING_FILES, MSG_INVALID_GUIDELINE, GUIDELINE_FILENAME,
    CSV_CONTENT_TYPE, OPENPYXL_ENGINE, BASE_TEST_DATA_LOCATION,
    TEST_FORMAT_XLSX, GUIDELINE_FILE, INPUT_FILE,
    TEST_FORMAT_TXT, FORM_DATA_TYPE, SESSION_GUIDELINE_PATH,
    SESSION_SAVED_PATH, TEST_FORMAT_CSV
)
from app.services.directory_service import DirectoryService


@pytest.fixture(autouse=True)
def setup_and_cleanup():
    DirectoryService.ensure_upload_dirs()
    yield
    DirectoryService.cleanup_temp_files()
    for directory in [UPLOAD_FOLDER, TEMP_FOLDER]:
        if os.path.exists(directory):
            os.rmdir(directory)


def create_test_excel(data) -> BytesIO:
    buffer: BytesIO = BytesIO()
    with pd.ExcelWriter(buffer, engine=OPENPYXL_ENGINE) as writer:
        pd.DataFrame(data).to_excel(writer, index=False)
    buffer.seek(0)

    return buffer


def setup_test_file_data() -> Dict:
    guideline_data: DataFrame = pd.DataFrame(BASE_TEST_DATA_LOCATION)
    input_data: DataFrame = pd.DataFrame({'Name': [], 'Age': []})
    guideline_buffer: BytesIO = BytesIO()

    guideline_data.to_csv(guideline_buffer, index=False)
    guideline_buffer.seek(0)

    input_buffer: BytesIO = create_test_excel(input_data)

    return {
        GUIDELINE_FILE: (guideline_buffer, GUIDELINE_FILENAME),
        INPUT_FILE: (input_buffer, TEST_FORMAT_XLSX)
    }


class TestRoutes:
    def test_upload_no_files(self, client) -> None:
        response: Response = client.post('/', data={})

        assert response.status_code == 200
        assert MSG_MISSING_FILES.encode() in response.data

    def test_upload_invalid_guideline_format(self, client) -> None:
        data: Dict = {
            GUIDELINE_FILE: (BytesIO(b'invalid'), TEST_FORMAT_TXT),
            INPUT_FILE: (create_test_excel({'Name': []}), TEST_FORMAT_XLSX)
        }

        response: Response = client.post('/', data=data, content_type=FORM_DATA_TYPE)

        assert response.status_code == 200
        assert MSG_INVALID_GUIDELINE.encode() in response.data

    def test_file_size_limit(self, client) -> None:
        large_data: bytes = b'0' * (MAX_FILE_SIZE_BYTES + 1024)
        data: Dict = {
            GUIDELINE_FILE: (BytesIO(b'header\n'), GUIDELINE_FILENAME),
            INPUT_FILE: (BytesIO(large_data), 'large.xlsx')
        }

        response = client.post('/', data=data, content_type=FORM_DATA_TYPE)

        assert response.status_code == 413

    def test_successful_upload_and_merge(self, client):
        guideline_data = pd.DataFrame({
            "Source Application": ["app1"],
            "Source Environment": ["prod"],
            "Destination Application": ["dest1"],
            "Num Flows": [100]
        })

        input_data = pd.DataFrame({
            "Source App Label": ["app1"],
            "Source Env": ["prod"],
            "Destination App Label": ["dest1"],
            "Total Connection Count": [100]
        })

        guideline_buffer = BytesIO()
        guideline_data.to_csv(guideline_buffer, index=False)
        guideline_buffer.seek(0)

        input_buffer = BytesIO()
        with pd.ExcelWriter(input_buffer, engine='openpyxl') as writer:
            input_data.to_excel(writer, index=False)
        input_buffer.seek(0)

        data = {
            GUIDELINE_FILE: (guideline_buffer, GUIDELINE_FILENAME),
            INPUT_FILE: (input_buffer, TEST_FORMAT_XLSX)
        }

        response = client.post('/', data=data, content_type=FORM_DATA_TYPE)
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')
        download_button = soup.find('button', {'class': 'download-btn'})
        assert download_button is not None
        file_id = download_button.get('data-file-id')
        assert file_id is not None

        response = client.get(f'/merge_and_download/{file_id}')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == CSV_CONTENT_TYPE

        result_df = pd.read_csv(StringIO(response.get_data(as_text=True)))
        expected_df = pd.DataFrame({
            "Source Application": ["app1"],
            "Source Environment": ["prod"],
            "Destination Application": ["dest1"],
            "Num Flows": [100]
        })

        pd.testing.assert_frame_equal(result_df[expected_df.columns], expected_df)

    def test_merge_invalid_session(self, client) -> None:
        with client.session_transaction() as session:
            session.clear()

        response: Response = client.get('/merge_and_download/any-id')

        assert response.status_code == 400

    def test_merge_invalid_file_id(self, client) -> None:
        with client.session_transaction() as session:
            session[SESSION_GUIDELINE_PATH] = 'some_path'
            session[SESSION_SAVED_PATH] = []

        response: Response = client.get('/merge_and_download/invalid-id')

        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main()