import os
from typing import Dict, Union

from flask import Blueprint, render_template, request, flash, make_response, session, Response, send_file, url_for, redirect
import pandas as pd
from pandas import DataFrame
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename

from app.services.file_service import FileService
from app.services.merge_service import MergeService
from app.services.directory_service import DirectoryService
from app.modules.app_status import AppStatusService
from app.utils.constants import (
    ERROR, MSG_MISSING_FILES, MSG_INVALID_GUIDELINE,
    MSG_SESSION_EXPIRED, MSG_FILE_NOT_FOUND, CSV_CONTENT_TYPE,
    INPUT_FILE, GUIDELINE_FILE, SESSION_GUIDELINE_PATH,
    SESSION_SAVED_PATH, UPLOAD_TEMPLATE, RESULTS_TEMPLATE,
    OUTPUT_FILE
)

main: Blueprint = Blueprint('main', __name__)

@main.route('/')
def index() -> str:
    """Homepage route"""
    return render_template('index.html')

@main.route('/excel-validation', methods=['GET', 'POST'])
def excel_validation() -> str:
    """Excel validation tool route"""
    DirectoryService.ensure_upload_dirs()

    if request.method == 'POST':
        if GUIDELINE_FILE not in request.files or INPUT_FILE not in request.files:
            flash(MSG_MISSING_FILES, ERROR)
            return render_template(UPLOAD_TEMPLATE)

        guideline_file: FileStorage = request.files[GUIDELINE_FILE]
        input_files: list[FileStorage] = request.files.getlist(INPUT_FILE)

        if guideline_file.filename == '' or not FileService.allowed_guideline_file(guideline_file.filename):
            flash(MSG_INVALID_GUIDELINE, ERROR)
            return render_template(UPLOAD_TEMPLATE)

        try:
            guideline_path, session_id = FileService.save_guideline_file(guideline_file)
            guideline_df: DataFrame = FileService.process_guideline_file(guideline_path)
        except Exception as e:
            print(f"Error processing guideline file: {str(e)}")
            FileService.cleanup_file(guideline_path)
            flash(MSG_INVALID_GUIDELINE, ERROR)
            return render_template(UPLOAD_TEMPLATE)

        results: list = []
        saved_files: list = []

        for file in input_files:
            if file and FileService.allowed_input_file(file.filename):
                try:
                    filepath, file_id = FileService.save_input_file(file)
                    input_df: DataFrame = FileService.process_input_file(filepath)

                    header_comparison: Dict = MergeService.compare_headers(guideline_df, input_df)

                    results.append({
                        'filename': file.filename,
                        'file_id': file_id,
                        'missing_headers': header_comparison.get('missing_headers', []),
                        'extra_headers': header_comparison.get('extra_headers', []),
                        'matched_headers': header_comparison.get('matched_headers', [])
                    })

                    saved_files.append({
                        'id': file_id,
                        'path': filepath,
                        'original_name': file.filename
                    })
                except Exception as e:
                    flash(f'Error processing {file.filename}: {str(e)}', ERROR)
                    FileService.cleanup_file(filepath)

        session[SESSION_GUIDELINE_PATH] = guideline_path
        session[SESSION_SAVED_PATH] = saved_files
        return render_template(RESULTS_TEMPLATE, results=results)

    return render_template(UPLOAD_TEMPLATE)

@main.route('/app-status', methods=['GET', 'POST'])
def app_status() -> str:
    """App status tool route"""
    if request.method == 'POST':
        if 'app_file' not in request.files or 'workload_file' not in request.files:
            flash('Please upload both required files', ERROR)
            return render_template('app_status.html')

        app_file = request.files['app_file']
        workload_file = request.files['workload_file']

        if app_file.filename == '' or workload_file.filename == '':
            flash('No file selected', ERROR)
            return render_template('app_status.html')

        try:
            # Read the CSV files into DataFrames
            try:
                app_df = pd.read_csv(app_file)
            except Exception as e:
                flash(f'Error reading app file: {str(e)}', ERROR)
                return render_template('app_status.html')

            try:
                workload_df = pd.read_csv(workload_file)
            except Exception as e:
                flash(f'Error reading workload file: {str(e)}', ERROR)
                return render_template('app_status.html')

            # Process the files
            service = AppStatusService()
            service.process_applications(app_df, workload_df)

            return render_template('app_status.html', result_file=OUTPUT_FILE)

        except Exception as e:
            flash(f'Error processing files: {str(e)}', ERROR)
            return render_template('app_status.html')

    return render_template('app_status.html')

@main.route('/download-report/<filename>')
def download_report(filename: str) -> Response:
    """Download generated report"""
    try:
        return send_file(
            filename,
            mimetype=CSV_CONTENT_TYPE,
            as_attachment=True,
            download_name='app_status_report.csv'
        )
    except Exception as e:
        flash(f'Error downloading report: {str(e)}', ERROR)
        return redirect(url_for('app_status'))

@main.route('/merge_and_download/<file_id>', methods=['GET', 'POST'])
def merge_and_download(file_id) -> Response | tuple[str, int]:
    try:
        if SESSION_GUIDELINE_PATH not in session or SESSION_SAVED_PATH not in session:
            raise BadRequest(MSG_SESSION_EXPIRED)

        input_file = next(
            (f for f in session[SESSION_SAVED_PATH] if f['id'] == file_id),
            None
        )

        if not input_file:
            raise BadRequest(MSG_FILE_NOT_FOUND)

        # Get custom mappings from request if this is a POST
        custom_mappings = request.json.get('mappings', {}) if request.method == 'POST' else None

        merged_content: str = MergeService.merge_files(
            session[SESSION_GUIDELINE_PATH],
            input_file['path'],
            custom_mappings=custom_mappings
        )

        original_name = os.path.splitext(input_file["original_name"])[0]
        safe_filename: str = secure_filename(f"{original_name}")

        response: Response = make_response(merged_content)
        response.headers['Content-Disposition'] = f'attachment; filename={safe_filename}.csv'
        response.headers['Content-Type'] = CSV_CONTENT_TYPE
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        return str(e), 400