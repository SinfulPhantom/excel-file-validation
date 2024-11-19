from flask import Blueprint, render_template, request, flash
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import pandas as pd
import os

main = Blueprint('main', __name__)

ALLOWED_INPUT_EXTENSIONS = {'xlsx', 'xls'}
ALLOWED_GUIDELINE_EXTENSION = {'csv'}
UPLOAD_FOLDER = 'app/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_input_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_INPUT_EXTENSIONS


def allowed_guideline_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_GUIDELINE_EXTENSION


@main.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'guideline_file' not in request.files:
            flash('No guideline file selected', 'error')
            return render_template('upload.html')

        if 'input_files' not in request.files:
            flash('No input files selected', 'error')
            return render_template('upload.html')

        guideline_file: FileStorage = request.files['guideline_file']
        input_files = request.files.getlist('input_files')

        if guideline_file.filename == '':
            flash('No guideline file selected', 'error')
            return render_template('upload.html')

        if not any(file.filename != '' for file in input_files):
            flash('No input files selected', 'error')
            return render_template('upload.html')

        if not allowed_guideline_file(guideline_file.filename):
            flash('Guideline file must be CSV format', 'error')
            return render_template('upload.html')

        results = []
        guideline_df = pd.read_csv(guideline_file)
        guideline_headers = set(guideline_df.columns)

        for input_file in input_files:
            if input_file.filename != '' and allowed_input_file(input_file.filename):
                filename = secure_filename(input_file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                input_file.save(filepath)

                try:
                    # Explicitly specify engine based on file extension
                    if filename.endswith('.xlsx'):
                        input_df = pd.read_excel(filepath, engine='openpyxl')
                    else:
                        input_df = pd.read_excel(filepath, engine='xlrd')

                    input_headers = set(input_df.columns)

                    missing_in_input = guideline_headers - input_headers
                    extra_in_input = input_headers - guideline_headers

                    results.append({
                        'filename': filename,
                        'missing_headers': sorted(list(missing_in_input)),
                        'extra_headers': sorted(list(extra_in_input))
                    })
                except Exception as e:
                    flash(f'Error processing {filename}: {str(e)}', 'error')
                finally:
                    if os.path.exists(filepath):
                        os.remove(filepath)
            else:
                flash(f'Invalid input file format: {input_file.filename}', 'error')

        return render_template('results.html', results=results)

    return render_template('upload.html')