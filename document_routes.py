from flask import Blueprint, request, jsonify
from db import get_db

document_bp = Blueprint('documents', __name__)

@document_bp.route('/api/documents/save', methods=['POST'])
def save_document():
    db = get_db()
    data = request.json

    required_fields = ["user_id", "name", "surname", "pesel"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Brakuje pola {field}"}), 400

    # Tutaj zapisz do bazy (tymczasowo id=123)
    document_id = 123

    return jsonify({"id": document_id})
