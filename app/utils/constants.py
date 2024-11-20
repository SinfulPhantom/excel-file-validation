import os
from typing import Dict

# File size limits
MAX_FILE_SIZE_MB: int = 75
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

# Read engines
OPENPYXL_ENGINE: str = 'openpyxl'
XLRD_ENGINE: str = 'xlrd'

# File extensions
ALLOWED_INPUT_EXTENSIONS: set[str] = {'xlsx', 'xls'}
ALLOWED_GUIDELINE_EXTENSION: set[str] = {'csv'}

# Template files
UPLOAD_TEMPLATE = 'upload.html'
RESULTS_TEMPLATE = 'results.html'

# Headers
HEADERS_MISSING: str = 'missing_headers'
HEADERS_EXTRA: str = 'extra_headers'
HEADERS_MATCHED: str = 'matched_headers'

# Content types
CSV_CONTENT_TYPE: str = 'text/csv'
FORM_DATA_TYPE: str = 'multipart/form-data'
EXCEL_CONTENT_TYPE: str = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

# Directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER: str = os.path.join(BASE_DIR, 'uploads')
TEMP_FOLDER: str = os.path.join(BASE_DIR, 'temp')
SESSION_GUIDELINE_PATH: str = 'guideline_path'
SESSION_SAVED_PATH: str = 'saved_files'

# Flask configurations
SECRET_KEY: str = 'dev'

# Flash message categories
ERROR: str = 'error'
SUCCESS: str = 'success'
WARNING: str = 'warning'

# Flash messages
MSG_MISSING_FILES: str = 'Missing files'
MSG_INVALID_GUIDELINE: str = 'Invalid guideline format'
MSG_FILE_TOO_LARGE: str = f'File size exceeds {MAX_FILE_SIZE_MB}MB limit'
MSG_SESSION_EXPIRED: str = 'Session expired'
MSG_FILE_NOT_FOUND: str = 'File not found'
MSG_ENCRYPTED_FILE: str = "This Excel file appears to be password protected. Please provide an unencrypted file."

# Files
TEST_FORMAT_XLSX: str = 'test.xlsx'
TEST_FORMAT_XLS: str = 'test.xls'
TEST_FORMAT_CSV: str = 'test.csv'
TEST_FORMAT_TXT: str = 'test.txt'
TEST_EXCEL_INPUT: str = "input.xlsx"
GUIDELINE_FILENAME: str = "guideline.csv"
GUIDELINE_FILE: str = 'guideline_file'
INPUT_FILE: str = 'input_files'

# Data
BASE_TEST_DATA_LOCATION: Dict = {
    'Name': [],
    'Age': [],
    'Location': []
}
BASE_TEST_DATA_EMAIL: Dict = {
    'Name': [],
    'Age': [],
    'Email': []
}

# Mapping
HEADER_CONVERSIONS: Dict = {
    "Consumer": "Source",
    "Consuming": "Source",
    "Provider": "Destination",
    "Providing": "Destination",
    "Services": "Ports"
}
ABBREVIATIONS_MAP: Dict = {
    'app': 'Application',
    'env': 'Environment',
    'loc': 'Location',
    'ost': 'OperatingSystem'
}