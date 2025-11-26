#!/usr/bin/env python3
import os
from datetime import datetime
from flask import Flask, jsonify, request, send_file, send_from_directory, Response
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)
CORS(app)

# --- DATABASE HELPERS ---
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    """Return a database connection"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    """Initialize database tables"""
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not set - skipping database initialization")
        return

    try:
        print("Connecting to database...")
        conn = get_db()
        cur = conn.cursor()
        print("Connection successful")

        # Users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                has_access BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            );
        ''')

        # Generated documents table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS generated_documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                name VARCHAR(255),
                surname VARCHAR(255),
                pesel VARCHAR(11),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data JSON
            );
        ''')

        # Seed admin user if not exists
        try:
            cur.execute(
                'INSERT INTO users (username, password, has_access, is_admin) VALUES (%s, %s, %s, %s)',
                ('mamba', 'MangoMango67', True, True)
            )
            conn.commit()
            print("✓ Admin user 'mamba' created successfully!")
        except psycopg.IntegrityError:
            print("✓ Admin user 'mamba' already exists")

        cur.close()
        conn.close()
        print("✓ Database initialization completed successfully!")
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        import traceback
        traceback.print_exc()


# --- STATIC / HTML FILES ---
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    try:
        return send_from_directory('assets', filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

def serve_html(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        response = Response(content, mimetype='text/html; charset=utf-8')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    except Exception as e:
        return jsonify({'error': f'Cannot load {filename}: {str(e)}'}), 500

@app.route('/')
def index():
    return serve_html('admin-login.html')

@app.route('/admin-login.html')
def admin_login_page():
    return serve_html('admin-login.html')

@app.route('/login.html')
def login_page():
    return serve_html('login.html')

@app.route('/gen.html')
def gen_page():
    return serve_html('gen.html')

@app.route('/manifest.json')
def manifest():
    try:
        with open('manifest.json', 'r', encoding='utf-8') as f:
            content = f.read()
        response = Response(content, mimetype='application/manifest+json')
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/admin.html')
def admin_page():
    return serve_html('admin.html')


# --- AUTH ROUTES ---
@app.route('/api/auth/create-user', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO users (username, password, has_access) VALUES (%s, %s, %s)',
            (username, password, True)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'User created successfully'}), 201
    except psycopg.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or user['password'] != password:
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user['has_access']:
            return jsonify({'error': 'Access denied. Contact administrator'}), 403

        return jsonify({
            'user_id': user['id'],
            'username': user['username'],
            'is_admin': user['is_admin']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- DOCUMENT ROUTES ---
@app.route('/api/documents/save', methods=['POST'])
def save_document():
    data = request.get_json()
    user_id = data.get("user_id")
    content = data.get("content")
    if not user_id or not content:
        return jsonify({"error": "Missing user_id or content"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO generated_documents (user_id, data) VALUES (%s, %s) RETURNING id',
            (user_id, content)
        )
        doc_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"id": doc_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/download/<int:doc_id>', methods=['GET'])
def download_document(doc_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM generated_documents WHERE id = %s', (doc_id,))
        doc = cur.fetchone()
        cur.close()
        conn.close()

        if not doc:
            return jsonify({'error': 'Document not found'}), 404

        filename = f"{doc['name']}_{doc['surname']}.pdf"
        pdf_path = generate_pdf_from_data(doc)  # <- implementacja po Twojej stronie
        return send_file(pdf_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- ADMIN ROUTES ---
@app.route('/api/admin/users', methods=['GET'])
def get_users():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id, username, has_access, created_at FROM users ORDER BY created_at DESC')
        users = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<int:user_id>/access', methods=['PUT'])
def update_access(user_id):
    data = request.get_json()
    has_access = data.get('has_access')
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('UPDATE users SET has_access=%s WHERE id=%s', (has_access, user_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Access updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/documents', methods=['GET'])
def get_all_documents():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            SELECT d.id, u.username, d.name, d.surname, d.pesel, d.created_at
            FROM generated_documents d
            JOIN users u ON d.user_id = u.id
            ORDER BY d.created_at DESC
        ''')
        documents = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(documents)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- INIT DB ON STARTUP ---
init_db()

# --- RUN ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
