from typing import Dict
import pytest
import os
from flask import Flask
from pandas import DataFrame
from app import create_app
import pandas as pd
from io import BytesIO
from werkzeug.datastructures import FileStorage
from app.utils.constants import (
    EXCEL_CONTENT_TYPE, UPLOAD_FOLDER, GUIDELINE_FILENAME,
    BASE_TEST_DATA_LOCATION, CSV_CONTENT_TYPE, OPENPYXL_ENGINE, TEST_FORMAT_XLSX
)


@pytest.fixture
def app():
    app: Flask = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    yield app

    if os.path.exists(UPLOAD_FOLDER):
        for file in os.listdir(UPLOAD_FOLDER):
            os.remove(os.path.join(UPLOAD_FOLDER, file))
        os.rmdir(UPLOAD_FOLDER)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def guideline_file() -> FileStorage:
    data: Dict = BASE_TEST_DATA_LOCATION
    df: DataFrame = pd.DataFrame(data)
    csv_buffer: BytesIO = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return FileStorage(
        stream=csv_buffer,
        filename=GUIDELINE_FILENAME,
        content_type=CSV_CONTENT_TYPE
    )

@pytest.fixture
def valid_excel_file() -> FileStorage:
    data: Dict = BASE_TEST_DATA_LOCATION
    df: DataFrame = pd.DataFrame(data)
    excel_buffer: BytesIO = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine=OPENPYXL_ENGINE) as writer:
        df.to_excel(writer, index=False)

    excel_buffer.seek(0)

    return FileStorage(
        stream=excel_buffer,
        filename=TEST_FORMAT_XLSX,
        content_type=EXCEL_CONTENT_TYPE
    )