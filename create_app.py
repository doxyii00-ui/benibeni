from flask import Flask
from document_routes import document_bp
from db import init_db  # jeśli masz konfigurację bazy

def create_app():
    app = Flask(__name__, static_folder='.', static_url_path='')

    # jeśli używasz bazy:
    init_db(app)

    # Rejestracja blueprintów
    app.register_blueprint(document_bp)

    return app
