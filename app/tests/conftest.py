import pytest
import os
from app import create_app
import pandas as pd
from io import BytesIO
from werkzeug.datastructures import FileStorage

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    os.makedirs('app/uploads', exist_ok=True)
    yield app
    if os.path.exists('app/uploads'):
        for file in os.listdir('app/uploads'):
            os.remove(os.path.join('app/uploads', file))
        os.rmdir('app/uploads')

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def guideline_file():
    data = {
        'Name': [],
        'Age': [],
        'Location': []
    }
    df = pd.DataFrame(data)
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return FileStorage(
        stream=csv_buffer,
        filename='guideline.csv',
        content_type='text/csv'
    )

@pytest.fixture
def valid_excel_file():
    data = {
        'Name': [],
        'Age': [],
        'Email': []
    }
    df = pd.DataFrame(data)
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    excel_buffer.seek(0)
    return FileStorage(
        stream=excel_buffer,
        filename='test.xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )