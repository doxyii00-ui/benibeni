# document_routes.py
from flask import Blueprint, request, jsonify
from db import get_db  # <- importujemy tylko z db.py

document_bp = Blueprint('documents', __name__)

@document_bp.route('/api/documents/save', methods=['POST'])
def save_document():
    db = get_db()
    data = request.json
    # zapis do bazy danych
    return jsonify({"id": 123})
