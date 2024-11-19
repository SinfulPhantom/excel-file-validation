import os
from app.utils.constants import UPLOAD_FOLDER, TEMP_FOLDER

class DirectoryService:
    @staticmethod
    def ensure_upload_dirs() -> None:
        """Ensure all required directories exist"""
        for directory in [UPLOAD_FOLDER, TEMP_FOLDER]:
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    def cleanup_temp_files() -> None:
        """Clean up temporary files"""
        for directory in [UPLOAD_FOLDER, TEMP_FOLDER]:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    try:
                        os.remove(os.path.join(directory, file))
                    except:
                        pass