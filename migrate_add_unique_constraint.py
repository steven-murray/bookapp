"""
Migration script to add unique constraint on author+title to the Book table.
This prevents duplicate books from being added.

Run this script after updating the models.py file with the new constraint.
"""

from app import app, db
from models import Book
from sqlalchemy import text

def add_unique_constraint():
    with app.app_context():
        # Check if we're using SQLite or PostgreSQL
        engine = db.engine
        dialect = engine.dialect.name
        
        print(f"Database dialect: {dialect}")
        
        # First, identify and remove any duplicate books
        # Keep the oldest version of each duplicate
        duplicates_query = text("""
            SELECT author, title, COUNT(*) as count, MIN(id) as keep_id
            FROM book
            GROUP BY author, title
            HAVING COUNT(*) > 1
        """)
        
        with engine.connect() as conn:
            result = conn.execute(duplicates_query)
            duplicates = result.fetchall()
            
            if duplicates:
                print(f"\nFound {len(duplicates)} sets of duplicate books:")
                for row in duplicates:
                    author, title, count, keep_id = row
                    print(f"  - '{title}' by {author}: {count} copies (keeping id={keep_id})")
                
                # For each set of duplicates, delete all except the one we're keeping
                for row in duplicates:
                    author, title, count, keep_id = row
                    
                    # Get all IDs for this author+title combination
                    find_dups = text("""
                        SELECT id FROM book
                        WHERE author = :author AND title = :title
                        AND id != :keep_id
                    """)
                    dup_ids_result = conn.execute(find_dups, {
                        'author': author,
                        'title': title,
                        'keep_id': keep_id
                    })
                    dup_ids = [row[0] for row in dup_ids_result.fetchall()]
                    
                    if dup_ids:
                        print(f"  Deleting duplicate IDs: {dup_ids}")
                        
                        # Delete related records first (to avoid FK constraints)
                        for table in ['reading_list_item', 'book_read', 'review', 'suggested_book']:
                            delete_related = text(f"""
                                DELETE FROM {table}
                                WHERE book_id IN :ids
                            """)
                            conn.execute(delete_related, {'ids': tuple(dup_ids)})
                        
                        # Now delete the duplicate books
                        delete_books = text("""
                            DELETE FROM book
                            WHERE id IN :ids
                        """)
                        conn.execute(delete_books, {'ids': tuple(dup_ids)})
                        conn.commit()
                
                print("\nDuplicates removed.")
            else:
                print("\nNo duplicate books found.")
        
        # Now add the unique constraint
        print("\nAdding unique constraint on (author, title)...")
        
        try:
            with engine.connect() as conn:
                if dialect == 'sqlite':
                    # SQLite doesn't support adding constraints to existing tables
                    # We need to check if it exists in the new table definition
                    print("SQLite: The constraint will be applied when you recreate the database")
                    print("or when you create new tables with the updated models.py")
                    print("\nFor existing SQLite databases, the constraint is enforced at the application level.")
                    
                elif dialect == 'postgresql':
                    # PostgreSQL supports adding constraints
                    add_constraint = text("""
                        ALTER TABLE book
                        ADD CONSTRAINT uq_author_title UNIQUE (author, title)
                    """)
                    
                    try:
                        conn.execute(add_constraint)
                        conn.commit()
                        print("Unique constraint added successfully!")
                    except Exception as e:
                        if 'already exists' in str(e).lower():
                            print("Constraint already exists.")
                        else:
                            raise
                
                else:
                    print(f"Unknown dialect: {dialect}. Manual migration may be required.")
        
        except Exception as e:
            print(f"Error adding constraint: {e}")
            raise
        
        print("\nMigration complete!")
        print("\nNote: The application code now prevents duplicate books from being created,")
        print("and books with student reviews cannot be deleted.")

if __name__ == '__main__':
    add_unique_constraint()
