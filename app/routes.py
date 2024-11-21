import os
from typing import Dict

from flask import Blueprint, render_template, request, flash, make_response, session, Response
from pandas import DataFrame
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename

from app.services.file_service import FileService
from app.services.merge_service import MergeService
from app.services.directory_service import DirectoryService
from app.utils.constants import (
    ERROR, MSG_MISSING_FILES, MSG_INVALID_GUIDELINE,
    MSG_SESSION_EXPIRED, MSG_FILE_NOT_FOUND, CSV_CONTENT_TYPE,
    INPUT_FILE, GUIDELINE_FILE, SESSION_GUIDELINE_PATH,
    SESSION_SAVED_PATH, UPLOAD_TEMPLATE, RESULTS_TEMPLATE
)

main: Blueprint = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def upload_file() -> str:
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
            print(f"Error processing guideline file: {str(e)}")  # Debug print
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

@main.route('/merge_and_download/<file_id>')
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

        merged_content: str = MergeService.merge_files(
            session[SESSION_GUIDELINE_PATH],
            input_file['path']
        )

        original_name = os.path.splitext(input_file["original_name"])[0]
        safe_filename: str = secure_filename(f"{original_name}.csv")

        response: Response = make_response(merged_content)
        response.headers['Content-Disposition'] = f'attachment; filename={safe_filename}'
        response.headers['Content-Type'] = CSV_CONTENT_TYPE
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        return str(e), 400