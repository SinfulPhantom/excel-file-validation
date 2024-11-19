import os
import uuid
import pandas as pd
from pandas import DataFrame
from app.utils.constants import (
    UPLOAD_FOLDER, ALLOWED_INPUT_EXTENSIONS,
    ALLOWED_GUIDELINE_EXTENSION, OPENPYXL_ENGINE,
    EXCEL_XML_FILE_TYPE, XLRD_ENGINE
)

class FileService:
    @staticmethod
    def allowed_input_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_INPUT_EXTENSIONS

    @staticmethod
    def allowed_guideline_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_GUIDELINE_EXTENSION

    @staticmethod
    def save_guideline_file(file) -> tuple[str, str]:
        session_id: str = str(uuid.uuid4())
        guideline_path: str = os.path.join(UPLOAD_FOLDER, f"{session_id}_guideline.csv")
        file.save(guideline_path)

        return guideline_path, session_id

    @staticmethod
    def save_input_file(file) -> tuple[str, str]:
        file_id = str(uuid.uuid4())
        filepath: str = os.path.join(UPLOAD_FOLDER, f"{file_id}_{file.filename}")
        file.save(filepath)
        return filepath, file_id

    @staticmethod
    def process_guideline_file(filepath) -> DataFrame:
        return pd.read_csv(filepath)

    @staticmethod
    def process_input_file(filepath) -> DataFrame:
        engine: str = OPENPYXL_ENGINE if filepath.endswith(EXCEL_XML_FILE_TYPE) else XLRD_ENGINE
        return pd.read_excel(filepath, engine=engine)

    @staticmethod
    def cleanup_file(filepath):
        if os.path.exists(filepath):
            os.remove(filepath)