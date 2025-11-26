from flask import Blueprint, request, jsonify
from db import get_db

document_bp = Blueprint('documents', __name__)

@document_bp.route('/api/documents/save', methods=['POST'])
def save_document():
    data = request.json
    user_id = data.get("user_id")
    content = data.get("content")

    if not user_id or not content:
        return jsonify({"error": "Missing user_id or content"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO generated_documents (user_id, content) VALUES (%s, %s) RETURNING id;",
            (user_id, content)
        )
        doc_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"id": doc_id})
    except Exception as e:
        print("Błąd zapisu dokumentu:", e)
        return jsonify({"error": "Błąd zapisu dokumentu! Spróbuj ponownie."}), 500
