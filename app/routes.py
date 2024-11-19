from flask import Blueprint, render_template, request, flash, make_response, session
from werkzeug.utils import secure_filename
import pandas as pd
import os
import io
import uuid
from werkzeug.exceptions import BadRequest

main = Blueprint('main', __name__)

UPLOAD_FOLDER = 'app/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_INPUT_EXTENSIONS = {'xlsx', 'xls'}
ALLOWED_GUIDELINE_EXTENSION = {'csv'}
UPLOAD_FOLDER = 'app/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_input_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_INPUT_EXTENSIONS

def allowed_guideline_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_GUIDELINE_EXTENSION


def save_uploaded_file(file, prefix=''):
    filename = secure_filename(f"{prefix}_{file.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filepath


def ensure_upload_dirs():
    """Ensure all required directories exist"""
    dirs = [UPLOAD_FOLDER, 'app/temp']
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)

# Initialize required directories when the module loads
ensure_upload_dirs()

@main.route('/', methods=['GET', 'POST'])
def upload_file():
    ensure_upload_dirs()  # Check directories exist before each upload
    if request.method == 'POST':
        if 'guideline_file' not in request.files or 'input_files' not in request.files:
            flash('Missing files', 'error')
            return render_template('upload.html')

        guideline_file = request.files['guideline_file']
        input_files = request.files.getlist('input_files')

        if guideline_file.filename == '':
            flash('Missing files', 'error')
            return render_template('upload.html')

        if not allowed_guideline_file(guideline_file.filename):
            flash('Invalid guideline format', 'error')
            return render_template('upload.html')

        # Save guideline file
        session_id = str(uuid.uuid4())
        guideline_path = save_uploaded_file(guideline_file, session_id)

        try:
            # Validate guideline file is actually a CSV
            pd.read_csv(guideline_path)
        except Exception:
            os.remove(guideline_path)
            flash('Invalid guideline format', 'error')
            return render_template('upload.html')

        # Process each input file
        results = []
        saved_files = []
        guideline_df = pd.read_csv(guideline_path)
        guideline_headers = set(guideline_df.columns)

        for file in input_files:
            if file and allowed_input_file(file.filename):
                file_id = str(uuid.uuid4())
                filepath = save_uploaded_file(file, file_id)

                input_df = pd.read_excel(filepath, engine='openpyxl')
                input_headers = set(input_df.columns)

                results.append({
                    'filename': file.filename,
                    'file_id': file_id,
                    'missing_headers': sorted(list(guideline_headers - input_headers)),
                    'extra_headers': sorted(list(input_headers - guideline_headers))
                })

                saved_files.append({
                    'id': file_id,
                    'path': filepath,
                    'original_name': file.filename
                })

        # Store paths in session
        session['guideline_path'] = guideline_path
        session['saved_files'] = saved_files

        return render_template('results.html', results=results)

    return render_template('upload.html')


@main.route('/merge_and_download/<file_id>')
def merge_and_download(file_id):
    try:
        if 'guideline_path' not in session or 'saved_files' not in session:
            raise BadRequest('Session expired')

        input_file = next(
            (f for f in session['saved_files'] if f['id'] == file_id),
            None
        )

        if not input_file:
            raise BadRequest('File not found')

        # Read files
        guideline_df = pd.read_csv(session['guideline_path'])
        input_df = pd.read_excel(input_file['path'], engine='openpyxl')

        # Add missing columns
        missing_columns = set(guideline_df.columns) - set(input_df.columns)
        for column in missing_columns:
            input_df[column] = pd.NA

        # Create output
        output = io.StringIO()
        input_df.to_csv(output, index=False)
        output.seek(0)

        # Get original filename without extension and add .csv
        original_name = os.path.splitext(input_file["original_name"])[0]

        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={original_name}.csv'
        response.headers['Content-Type'] = 'text/csv'

        return response

    except Exception as e:
        return str(e), 400

    finally:
        if 'saved_files' not in session:
            cleanup_files()


def cleanup_files():
    for file in os.listdir(UPLOAD_FOLDER):
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, file))
        except:
            pass