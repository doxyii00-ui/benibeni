# db.py
from flask import g
import sqlite3  # lub psycopg2 jeśli używasz PostgreSQL

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('mydb.sqlite')
    return g.db
