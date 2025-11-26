# document_routes.py
from flask import Blueprint, request, jsonify
from db import get_db  # zakładamy, że masz funkcję get_db() w db.py
from psycopg.rows import dict_row

document_bp = Blueprint('documents', __name__)

@document_bp.route('/api/documents/save', methods=['POST'])
def save_document():
    db = get_db()
    data = request.json

    if not data or 'title' not in data or 'content' not in data:
        return jsonify({"error": "Nieprawidłowe dane"}), 400

    try:
        with db.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO documents (title, content, created_at)
                VALUES (%s, %s, NOW())
                RETURNING id
                """,
                (data['title'], data['content'])
            )
            doc_id = cur.fetchone()['id']
            db.commit()

        return jsonify({"id": doc_id})

    except Exception as e:
        print("Błąd przy zapisie dokumentu:", e)
        return jsonify({"error": "Błąd zapisu dokumentu! Spróbuj ponownie."}), 500
