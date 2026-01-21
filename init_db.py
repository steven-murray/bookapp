"""
Initialize or update database schema.
This script creates all tables based on the SQLAlchemy models.
Safe to run multiple times - will only create missing tables.
"""
from app import app
from models import db

def init_db():
    with app.app_context():
        # Create all tables defined in models.py
        # This is safe to run - it only creates tables that don't exist
        db.create_all()
        print("Database tables created/verified successfully!")
        
        # Print all tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\nCurrent tables in database: {', '.join(tables)}")

if __name__ == '__main__':
    init_db()
