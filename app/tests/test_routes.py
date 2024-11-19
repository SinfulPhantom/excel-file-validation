from io import BytesIO
from werkzeug.datastructures import FileStorage


def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'File Validator' in response.data

def test_upload_no_files(client):
    response = client.post('/')
    assert response.status_code == 200
    assert b'No guideline file selected' in response.data

def test_upload_missing_input_files(client, guideline_file):
    data = {
        'guideline_file': guideline_file
    }
    response = client.post('/', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'No input files selected' in response.data

def test_upload_invalid_guideline_format(client):
    invalid_file = FileStorage(
        stream=BytesIO(b'invalid'),
        filename='test.txt',
        content_type='text/plain'
    )
    data = {
        'guideline_file': invalid_file,
        'input_files': (BytesIO(b'invalid'), 'test.xlsx')
    }
    response = client.post('/', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'Guideline file must be CSV format' in response.data

def test_successful_file_comparison(client, guideline_file, valid_excel_file):
    data = {
        'guideline_file': guideline_file,
        'input_files': valid_excel_file
    }
    response = client.post('/', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'Location' in response.data
    assert b'Email' in response.data

def test_multiple_file_upload(client, guideline_file):
    # Create two different test files
    excel_data = b'PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    excel_file1 = FileStorage(
        stream=BytesIO(excel_data),
        filename='test1.xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    excel_file2 = FileStorage(
        stream=BytesIO(excel_data),
        filename='test2.xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    data = {
        'guideline_file': guideline_file,
        'input_files': [excel_file1, excel_file2]
    }

    response = client.post('/',
                           data=data,
                           content_type='multipart/form-data')

    assert response.status_code == 200
    # Check for file processing attempt rather than specific content
    assert b'test1.xlsx' in response.data
    assert b'test2.xlsx' in response.data