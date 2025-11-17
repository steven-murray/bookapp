import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # Support DATABASE_URL (Render/Heroku) and DATABASE_URI (local)
    _db_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URI')
    if _db_url and _db_url.startswith('postgres://'):
        # SQLAlchemy expects postgresql://
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url or 'sqlite:///' + os.path.join(basedir, 'bookapp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENLIBRARY_API_URL = 'https://openlibrary.org'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
