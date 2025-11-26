# create_app.py
from flask import Flask

def create_app():
    app = Flask(__name__)

    # importujemy blueprinty tutaj, po utworzeniu app
    from document_routes import document_bp
    app.register_blueprint(document_bp)

    return app
