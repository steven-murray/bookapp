import csv
import io
from models import Book, db
from openlibrary_service import OpenLibraryService

class BookImportService:
    """Service for importing books from CSV files"""
    
    @staticmethod
    def import_from_csv(csv_file) -> dict:
        """
        Import books from CSV file
    Expected CSV format: title, author, isbn, book_type, genre, sub_genre, topic, lexile_rating, grade, owned
        Returns dict with success count and errors
        """
        result = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        try:
            # Read CSV file
            stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
                try:
                    # Check if book already exists
                    isbn = row.get('isbn', '').strip()
                    if isbn:
                        existing_book = Book.query.filter_by(isbn=isbn).first()
                        if existing_book:
                            result['errors'].append(f"Row {row_num}: Book with ISBN {isbn} already exists")
                            result['error_count'] += 1
                            continue
                    
                    # Create book from CSV data
                    # Parse grade
                    grade_val = None
                    grade_raw = (row.get('grade') or '').strip()
                    if grade_raw:
                        try:
                            grade_val = int(grade_raw)
                        except ValueError:
                            raise ValueError(f"Invalid grade '{grade_raw}'")
                        if grade_val < 1 or grade_val > 12:
                            raise ValueError(f"Grade must be between 1 and 12 (got {grade_val})")

                    # Parse owned
                    owned_val = (row.get('owned') or '').strip() or 'Not Owned'
                    if owned_val not in ['Physical', 'Kindle', 'Not Owned']:
                        raise ValueError(f"Invalid owned value '{owned_val}' (must be Physical, Kindle, or Not Owned)")

                    book = Book(
                        title=row.get('title', '').strip(),
                        author=row.get('author', '').strip(),
                        isbn=isbn if isbn else None,
                        book_type=row.get('book_type', '').strip() or None,
                        genre=row.get('genre', '').strip(),
                        sub_genre=row.get('sub_genre', '').strip() or None,
                        topic=row.get('topic', '').strip(),
                        lexile_rating=row.get('lexile_rating', '').strip(),
                        grade=grade_val,
                        owned=owned_val
                    )
                    
                    # Try to enrich from OpenLibrary if ISBN is provided
                    if isbn:
                        try:
                            ol_data = OpenLibraryService.get_book_by_isbn(isbn)
                            if ol_data:
                                if not book.title:
                                    book.title = ol_data.get('title', '')
                                if not book.author:
                                    book.author = ol_data.get('author', '')
                                book.openlibrary_id = ol_data.get('openlibrary_id', '')
                                book.description = ol_data.get('description', '')
                                book.cover_url = ol_data.get('cover_url', '')
                                book.publication_year = ol_data.get('publication_year')
                                # Don't override genre/topic from CSV if they exist
                                if not book.genre and ol_data.get('genre'):
                                    book.genre = ol_data.get('genre', '')
                        except Exception as e:
                            # Continue even if OpenLibrary lookup fails
                            print(f"OpenLibrary lookup failed for {isbn}: {e}")
                    
                    # Validate required fields
                    if not book.title:
                        result['errors'].append(f"Row {row_num}: Title is required")
                        result['error_count'] += 1
                        continue
                    
                    db.session.add(book)
                    result['success_count'] += 1
                    
                except Exception as e:
                    result['errors'].append(f"Row {row_num}: {str(e)}")
                    result['error_count'] += 1
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            result['errors'].append(f"File processing error: {str(e)}")
            result['error_count'] += 1
        
        return result
    
    @staticmethod
    def create_sample_csv() -> str:
        """Generate sample CSV content for download"""
        sample_data = [
            ['title', 'author', 'isbn', 'book_type', 'genre', 'sub_genre', 'topic', 'lexile_rating', 'grade', 'owned'],
            ['The Hunger Games', 'Suzanne Collins', '9780439023481', 'Fiction', 'Science Fiction', 'Dystopian', 'Courage', '810L', '7', 'Physical'],
            ['Wonder', 'R.J. Palacio', '9780375869020', 'Fiction', 'Realistic Fiction', 'School Life', 'Kindness', '790L', '5', 'Kindle'],
            ['I Am Malala', 'Malala Yousafzai', '9780316322423', 'Non-Fiction', 'Biography', 'Memoir', 'Activism', '1000L', '8', 'Not Owned']
        ]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(sample_data)
        return output.getvalue()
