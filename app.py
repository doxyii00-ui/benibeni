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

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

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
    return serve_html('gen.html')

@app.route('/gen.html')
def gen_page():
    return serve_html('gen.html')

@app.route('/id.html')
def id_page():
    return serve_html('id.html')

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

# -------------------- Database --------------------
def get_db():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not set")
    return psycopg.connect(db_url)

def init_db():
    """Initialize database with required tables"""
    try:
        conn = get_db()
        cur = conn.cursor()
        # Users table (opcjonalnie, nie blokuje dostępu)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE,
                password VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Generated documents table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS generated_documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name VARCHAR(255),
                surname VARCHAR(255),
                pesel VARCHAR(11),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data JSON,
                public_id TEXT UNIQUE
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")

# -------------------- Documents --------------------
@app.route('/api/documents/save', methods=['POST'])
def save_document():
    data = request.get_json()
    try:
        public_id = secrets.token_urlsafe(16)
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO generated_documents (user_id, name, surname, pesel, data, public_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data.get('user_id'),
            data.get('name'),
            data.get('surname'),
            data.get('pesel'),
            json.dumps(data),
            public_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'public_id': public_id, 'link': f'/id.html?doc={public_id}'}), 201
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
            return jsonify({'error': 'Document not found'}), 404
        return jsonify(json.loads(row['data'])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------- Startup --------------------
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
