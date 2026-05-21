import os
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Flask-SQLAlchemy instance for the application
db = SQLAlchemy()


def get_database_uri():
    env_url = os.getenv('DATABASE_URL')
    if env_url:
        return env_url

    base_dir = Path(__file__).resolve().parent.parent
    return f"sqlite:///{base_dir / 'auralis.db'}"


@event.listens_for(Engine, 'connect')
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith('sqlite3'):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
