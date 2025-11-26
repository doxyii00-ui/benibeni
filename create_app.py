# create_app.py
from flask import Flask
from document_routes import document_bp

def create_app():
    app = Flask(__name__, static_folder='.', static_url_path='')

    # Rejestracja blueprintów
    app.register_blueprint(document_bp)

    return app
