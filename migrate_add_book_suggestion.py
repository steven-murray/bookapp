"""
Migration script to add the book_suggestion table for student book suggestions.

Run this script to create the new table in your database.
"""

from app import app, db
from models import BookSuggestion

def create_book_suggestion_table():
    with app.app_context():
        print("Creating book_suggestion table...")
        
        # Create the table
        db.create_all()
        
        print("✓ book_suggestion table created successfully!")
        print("\nThe table has the following structure:")
        print("  - id (primary key)")
        print("  - student_id (foreign key to user)")
        print("  - title")
        print("  - author")
        print("  - reason")
        print("  - status (pending/approved/rejected/added)")
        print("  - suggested_at")
        print("  - reviewed_at")
        print("  - reviewed_by_id (foreign key to user)")
        print("  - admin_notes")
        print("  - book_id (foreign key to book)")

if __name__ == '__main__':
    create_book_suggestion_table()
