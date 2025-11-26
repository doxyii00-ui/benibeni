import os
from flask import jsonify, request, send_file
from psycopg.rows import dict_row
from fpdf import FPDF  # pip install fpdf
from app import app, get_db


# ---------------------
# DODAWANIE DOKUMENTU
# ---------------------
@app.route('/api/documents/save', methods=['POST'])
def save_document():
    data = request.get_json()
    user_id = data.get('user_id')

    try:
        conn = get_db()
        cur = conn.cursor(row_factory=dict_row)

        cur.execute(
            '''
            INSERT INTO generated_documents (user_id, name, surname, pesel, data)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        ''',
            (user_id, data.get('name'), data.get('surname'), data.get('pesel'),
             str(data))
        )

        doc_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'document_id': doc_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------
# GENEROWANIE PDF PO ID
# ---------------------
@app.route('/api/documents/download/<int:doc_id>', methods=['GET'])
def download_document(doc_id):
    try:
        conn = get_db()
        cur = conn.cursor(row_factory=dict_row)

        cur.execute('SELECT * FROM generated_documents WHERE id = %s',
                    (doc_id,))
        doc = cur.fetchone()

        cur.close()
        conn.close()

        if not doc:
            return jsonify({'error': 'Document not found'}), 404

        pdf_path = generate_pdf_from_data(doc)

        safe_filename = f"dokument_{doc_id}.pdf"
        return send_file(pdf_path,
                         as_attachment=True,
                         download_name=safe_filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------
# FUNKCJA GENERUJĄCA PDF
# ---------------------
def generate_pdf_from_data(doc):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)

    pdf.cell(200, 10, txt="Wygenerowany Dokument", ln=1, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=f"Imię: {doc['name']}", ln=1)
    pdf.cell(200, 8, txt=f"Nazwisko: {doc['surname']}", ln=1)
    pdf.cell(200, 8, txt=f"PESEL: {doc['pesel']}", ln=1)
    pdf.cell(200, 8, txt=f"Użytkownik ID: {doc['user_id']}", ln=1)

    # TWORZYMY BEZPIECZNY PLIK PDF
    os.makedirs("generated_pdfs", exist_ok=True)
    filename = f"generated_pdfs/doc_{doc['id']}.pdf"
    pdf.output(filename)

    return filename
