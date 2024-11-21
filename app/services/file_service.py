import os
import uuid
from typing import Tuple, List

import pandas as pd
from pandas import DataFrame
from app.utils.constants import (
    UPLOAD_FOLDER, ALLOWED_INPUT_EXTENSIONS,
    ALLOWED_GUIDELINE_EXTENSION, OPENPYXL_ENGINE,
    XLRD_ENGINE, GUIDELINE_FILENAME, MSG_ENCRYPTED_FILE, MSG_ERROR
)


class FileService:
    @staticmethod
    def allowed_input_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_INPUT_EXTENSIONS

    @staticmethod
    def allowed_guideline_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_GUIDELINE_EXTENSION

    @staticmethod
    def save_guideline_file(file) -> Tuple[str, str]:
        session_id: str = str(uuid.uuid4())
        guideline_path: str = os.path.join(UPLOAD_FOLDER, f"{session_id}_{GUIDELINE_FILENAME}")
        file.save(guideline_path)
        return guideline_path, session_id

    @staticmethod
    def save_input_file(file) -> Tuple[str, str]:
        file_id = str(uuid.uuid4())
        filepath: str = os.path.join(UPLOAD_FOLDER, f"{file_id}_{file.filename}")
        file.save(filepath)
        return filepath, file_id

    @staticmethod
    def process_guideline_file(filepath: str) -> DataFrame:
        return pd.read_csv(filepath)

    @staticmethod
    def process_input_file(filepath: str) -> DataFrame:
        """
        Process input Excel file with multiple engine attempts and better error handling
        """
        exceptions: List = []

        # Try openpyxl first (for .xlsx)
        try:
            return pd.read_excel(filepath, engine=OPENPYXL_ENGINE)
        except Exception as e:
            error_msg = str(e).lower()
            if "not a zip file" in error_msg or "file is not a zip file" in error_msg:
                raise ValueError(MSG_ENCRYPTED_FILE)
            exceptions.append(f"openpyxl error: {str(e)}")

        # Try xlrd as fallback (for .xls)
        try:
            return pd.read_excel(filepath, engine=XLRD_ENGINE)
        except Exception as e:
            exceptions.append(f"xlrd error: {str(e)}")

        # If both engines fail, try with default engine
        try:
            return pd.read_excel(filepath)
        except Exception as e:
            exceptions.append(f"default engine error: {str(e)}")

        # If all attempts fail, raise a user-friendly error with technical details in logs
        print(f"Excel reading errors:\n" + "\n".join(exceptions))  # Log technical details
        raise ValueError(MSG_ERROR)

    @staticmethod
    def cleanup_file(filepath: str) -> None:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass