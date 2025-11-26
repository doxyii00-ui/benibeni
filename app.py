#!/usr/bin/env python3
import os
import json
import secrets
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
import bcrypt
import jwt

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

JWT_SECRET = os.environ.get('JWT_SECRET', 'supersecretkey')  # zmień w produkcji
JWT_ALGORITHM = 'HS256'
JWT_EXP_DAYS = 7

# -------------------- Static Files --------------------
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

# -------------------- Database --------------------
def get_db():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not set")
    return psycopg.connect(db_url)

def init_db():
    """Initialize database with required tables and ensure admin user exists"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("WARNING: DATABASE_URL not set - skipping database initialization")
        return

    try:
        conn = psycopg.connect(db_url)
        cur = conn.cursor()

        # -------------------- Users Table --------------------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                has_access BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            )
        ''')

        # -------------------- Generated Documents Table --------------------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS generated_documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                name VARCHAR(255),
                surname VARCHAR(255),
                pesel VARCHAR(11),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data JSON,
                public_id TEXT UNIQUE
            )
        ''')

        # -------------------- Seed Admin User --------------------
        admin_username = 'mamba'
        admin_plain_password = 'MangoMango67'
        hashed_password = bcrypt.hashpw(admin_plain_password.encode(), bcrypt.gensalt()).decode()

        cur.execute('''
            INSERT INTO users (username, password, has_access, is_admin)
            VALUES (%s, %s, TRUE, TRUE)
            ON CONFLICT (username)
            DO UPDATE SET password=EXCLUDED.password, has_access=TRUE, is_admin=TRUE
        ''', (admin_username, hashed_password))
        print(f"Admin user '{admin_username}' ensured with access and admin rights")

        # -------------------- Commit & Close --------------------
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()


# -------------------- Auth Helpers --------------------
def create_jwt(user_id, username, is_admin):
    payload = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXP_DAYS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def decode_jwt(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def auth_required(admin_only=False):
    """Decorator to protect routes"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization header missing'}), 401
            token = auth_header.split(' ')[1]
            payload = decode_jwt(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            if admin_only and not payload.get('is_admin'):
                return jsonify({'error': 'Admin access required'}), 403
            request.user = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator

# -------------------- Auth Routes --------------------
@app.route('/api/auth/create-user', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO users (username, password, has_access) VALUES (%s, %s, %s)',
            (username, hashed_password, True)
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
        cur = conn.cursor(row_factory=dict_row)
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or not bcrypt.checkpw(password.encode(), user['password'].encode()):
            return jsonify({'error': 'Invalid credentials'}), 401
        if not user['has_access']:
            return jsonify({'error': 'Access denied'}), 403

        token = create_jwt(user['id'], user['username'], user['is_admin'])
        return jsonify({'token': token, 'user': {'id': user['id'], 'username': user['username'], 'is_admin': user['is_admin']}}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------- Documents --------------------
@app.route('/api/documents/save', methods=['POST'])
@auth_required()
def save_document():
    data = request.get_json()
    user_id = request.user['user_id']
    try:
        public_id = secrets.token_urlsafe(16)
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO generated_documents (user_id, name, surname, pesel, data, public_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING public_id
        ''', (user_id, data.get('name'), data.get('surname'),
              data.get('pesel'), json.dumps(data), public_id))
        public_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'public_id': public_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
@auth_required()
def get_document(doc_id):
    user_id = request.user['user_id']
    try:
        conn = get_db()
        cur = conn.cursor(row_factory=dict_row)
        cur.execute('SELECT * FROM generated_documents WHERE id = %s AND user_id = %s', (doc_id, user_id))
        doc = cur.fetchone()
        cur.close()
        conn.close()
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        return jsonify(json.loads(doc['data'])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/public/<public_id>', methods=['GET'])
def get_public_document(public_id):
    try:
        conn = get_db()
        cur = conn.cursor(row_factory=dict_row)
        cur.execute('SELECT data FROM generated_documents WHERE public_id = %s', (public_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(json.loads(row['data'])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------- Admin Routes --------------------
@app.route('/api/admin/users', methods=['GET'])
@auth_required(admin_only=True)
def get_users():
    try:
        conn = get_db()
        cur = conn.cursor(row_factory=dict_row)
        cur.execute('SELECT id, username, has_access, created_at FROM users ORDER BY created_at DESC')
        users = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<int:user_id>/access', methods=['PUT'])
@auth_required(admin_only=True)
def update_access(user_id):
    data = request.get_json()
    has_access = data.get('has_access')
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('UPDATE users SET has_access = %s WHERE id = %s', (has_access, user_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Access updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/documents', methods=['GET'])
@auth_required(admin_only=True)
def get_all_documents():
    try:
        conn = get_db()
        cur = conn.cursor(row_factory=dict_row)
        cur.execute('''
            SELECT d.id, u.username, d.name, d.surname, d.pesel, d.created_at
            FROM generated_documents d
            JOIN users u ON d.user_id = u.id
            ORDER BY d.created_at DESC
        ''')
        documents = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(documents), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------- Startup --------------------
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
