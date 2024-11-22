# Excel File Header Validator

A Flask web application that validates and merges Excel files against a CSV guideline file.

## Features

- Upload guideline CSV file with expected headers
- Upload multiple Excel files for validation
- Compare headers between guideline and input files
- Identify missing, extra, and matched headers
- Merge and download files with standardized headers

## Tech Stack

- Python 3.x
- Flask
- Pandas
- BeautifulSoup4
- Bootstrap 5
- JavaScript

## Project Structure

```
excel-file-validation/
├── app/
│   ├── services/
│   │   ├── directory_service.py
│   │   ├── file_service.py
│   │   └── merge_service.py
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── validation.js
│   ├── templates/
│   │   ├── base.html
│   │   ├── results.html
│   │   └── upload.html
│   ├── tests/
│   │   ├── test_routes.py
│   │   └── test_services.py
│   └── utils/
│       └── constants.py
├── uploads/
└── temp/
```

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Unix/macOS
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Key configurations in `constants.py`:
- File size limits
- Allowed file extensions
- Header mappings
- Directory paths
- Flash messages

## Usage

1. Start the server:
```bash
flask run
```

2. Access the application at `http://localhost:5000`

3. Upload files:
   - Select a guideline CSV file
   - Select one or more Excel files
   - Click "Upload and Validate"

4. Review results:
   - View missing headers
   - Check matched headers
   - See extra headers
   - Download merged files

## Testing

Run tests with pytest:
```bash
pytest
```

Key test files:
- `test_routes.py`: Tests for HTTP endpoints
- `test_services.py`: Tests for service layer functionality

## Services

### DirectoryService
- Manages upload and temporary directories
- Handles file cleanup

### FileService
- Validates file types
- Processes file uploads
- Handles file operations

### MergeService
- Compares headers between files
- Performs header mapping
- Merges files with standardized headers

## Security

- File size limits enforced
- Secure filename handling
- No caching of sensitive data
- Session management for file operations