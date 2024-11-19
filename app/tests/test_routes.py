import os

import pytest
import pandas as pd
from io import BytesIO


@pytest.fixture
def cleanup():
    yield
    import os
    from app.routes import UPLOAD_FOLDER
    for file in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, file))


def test_upload_no_files(client, cleanup):
    data = {}
    response = client.post('/', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'Missing files' in response.data


def test_upload_missing_input_files(client, cleanup):
    guideline_data = pd.DataFrame({'Name': [], 'Age': [], 'Location': []})
    guideline_buffer = BytesIO()
    guideline_data.to_csv(guideline_buffer, index=False)
    guideline_buffer.seek(0)

    data = {
        'guideline_file': (guideline_buffer, 'guideline.csv')
    }
    response = client.post('/', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'Missing files' in response.data


def test_upload_invalid_guideline_format(client, cleanup):
    data = {
        'guideline_file': (BytesIO(b'invalid,content\nrow1,row2'), 'test.txt'),
        'input_files': (create_test_excel({'Name': [], 'Age': []}), 'test.xlsx')
    }
    response = client.post('/', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'Invalid guideline format' in response.data


def test_multiple_file_upload(client, cleanup):
    # Create guideline file
    guideline_data = pd.DataFrame({'Name': [], 'Age': [], 'Location': []})
    guideline_buffer = BytesIO()
    guideline_data.to_csv(guideline_buffer, index=False)
    guideline_buffer.seek(0)

    # Create two input files
    input_data1 = pd.DataFrame({'Name': [], 'Age': []})
    input_buffer1 = create_test_excel(input_data1)

    input_data2 = pd.DataFrame({'Name': [], 'Email': []})
    input_buffer2 = create_test_excel(input_data2)

    data = {
        'guideline_file': (guideline_buffer, 'guideline.csv'),
        'input_files': [
            (input_buffer1, 'test1.xlsx'),
            (input_buffer2, 'test2.xlsx')
        ]
    }

    response = client.post('/',
                           data=data,
                           content_type='multipart/form-data')

    assert response.status_code == 200
    assert b'test1.xlsx' in response.data
    assert b'test2.xlsx' in response.data


def create_test_excel(data):
    buffer = BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer


def test_merge_and_download(client, cleanup):
    guideline_data = pd.DataFrame({'Name': [], 'Age': [], 'Location': []})
    guideline_buffer = BytesIO()
    guideline_data.to_csv(guideline_buffer, index=False)
    guideline_buffer.seek(0)

    input_buffer = create_test_excel({'Name': [], 'Age': []})

    response = client.post('/', data={
        'guideline_file': (guideline_buffer, 'guideline.csv'),
        'input_files': (input_buffer, 'test.xlsx')
    }, content_type='multipart/form-data')

    assert response.status_code == 200

    import re
    match = re.search(r'data-file-id="([^"]+)"', response.data.decode())
    assert match is not None
    file_id = match.group(1)

    response = client.get(f'/merge_and_download/{file_id}')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert 'filename=test.csv' in response.headers['Content-Disposition']


def test_merge_missing_files(client, cleanup):
    response = client.get('/merge_and_download/nonexistent')
    assert response.status_code == 400


def test_merge_invalid_session(client, cleanup):
    with client.session_transaction() as session:
        session.clear()
    response = client.get('/merge_and_download/any-id')
    assert response.status_code == 400


def test_merge_invalid_file_id(client, cleanup):
    with client.session_transaction() as session:
        session['guideline_path'] = 'some_path'
        session['saved_files'] = []

    response = client.get('/merge_and_download/invalid-id')
    assert response.status_code == 400


@pytest.fixture
def clean_directories():
    """Fixture to clean up directories before and after tests"""
    import shutil
    from app.routes import UPLOAD_FOLDER

    # Clean before test
    for directory in [UPLOAD_FOLDER, 'app/temp']:
        if os.path.exists(directory):
            shutil.rmtree(directory)

    yield

    # Clean after test
    for directory in [UPLOAD_FOLDER, 'app/temp']:
        if os.path.exists(directory):
            shutil.rmtree(directory)


def test_directory_creation(client, clean_directories):
    from app.routes import UPLOAD_FOLDER

    # Verify directories don't exist initially
    assert not os.path.exists(UPLOAD_FOLDER)
    assert not os.path.exists('app/temp')

    # Access route and verify response
    response = client.get('/')
    assert response.status_code == 200

    # Verify directories were created
    assert os.path.exists(UPLOAD_FOLDER)
    assert os.path.exists('app/temp')
    assert os.path.isdir(UPLOAD_FOLDER)
    assert os.path.isdir('app/temp')

    # Verify directories are writable
    test_file_path = os.path.join(UPLOAD_FOLDER, 'test.txt')
    try:
        with open(test_file_path, 'w') as f:
            f.write('test')
        assert os.path.exists(test_file_path)
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)