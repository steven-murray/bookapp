"""
Migration script to add the BookEditSuggestion table for students to suggest edits to existing books.
"""
from bookapp.app import app
from bookapp.models import db

def migrate():
    with app.app_context():
        # Create the book_edit_suggestion table
        with db.engine.connect() as conn:
            # PostgreSQL-compatible version (works for both PostgreSQL and SQLite)
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS book_edit_suggestion (
                    id SERIAL PRIMARY KEY,
                    book_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    suggested_title VARCHAR(200),
                    suggested_author VARCHAR(200),
                    suggested_openlibrary_id VARCHAR(50),
                    suggested_publication_year INTEGER,
                    suggested_book_type VARCHAR(20),
                    suggested_genre VARCHAR(100),
                    suggested_sub_genre VARCHAR(100),
                    suggested_topic VARCHAR(100),
                    suggested_lexile_rating VARCHAR(20),
                    suggested_grade INTEGER,
                    suggested_description TEXT,
                    suggested_owned VARCHAR(50),
                    reason TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewed_by_id INTEGER,
                    admin_notes TEXT,
                    FOREIGN KEY (book_id) REFERENCES book (id),
                    FOREIGN KEY (student_id) REFERENCES user (id),
                    FOREIGN KEY (reviewed_by_id) REFERENCES user (id)
                )
            """))
            conn.commit()
        print("Created book_edit_suggestion table successfully!")

if __name__ == '__main__':
    migrate()
