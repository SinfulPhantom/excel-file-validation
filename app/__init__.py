from flask import Flask
from .routes import main
from app.utils.constants import SECRET_KEY, MAX_FILE_SIZE_BYTES


def create_app() -> Flask:
    app: Flask = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_BYTES

    app.register_blueprint(main)

    return app