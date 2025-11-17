import csv
import io
import re
from models import Book, db
from openlibrary_service import OpenLibraryService
from sqlalchemy import func

def enrich_book_from_openlibrary(b: Book) -> bool:
    if (b.book_type and b.genre and b.sub_genre and b.publication_year and b.cover_url and b.openlibrary_id):
        return False
    
    try:
        ol_data = OpenLibraryService.search_books(
            f"author:{b.author} title:{b.title}",
            fields=['author_name', 'title', 'subject', 'key', 'first_publish_year'], 
            limit=1
        )[0]
    except Exception as e:
        print(f"OpenLibrary lookup failed for {b.author} {b.title}: {e}")
        return False

    print(f"Processing book: {b.title} by {b.author}.")
    print(f"  > OpenLibrary data: {ol_data}")
    
    KNOWN_GENRES = [
        'Fantasy', 'Science Fiction', 'Mystery', 'Romance', 'Historical Fiction', 
        'Biography', 'Self-Help', 'Adventure', 'Horror', 'Thriller',
        'History', 'Science', 'Poetry', 'Drama', 'Children\'s Fiction', 'Young Adult'
    ]
    subjects = ol_data.get('subjects') or []
    lower_subjects = [s.lower() for s in subjects]
    changed = False
    if not b.book_type:
        if any(('nonfiction' in s) or ('non-fiction' in s) or ('non fiction' in s) for s in lower_subjects):
            b.book_type = 'Non-Fiction'
            changed = True
        elif 'fiction' in lower_subjects:
            b.book_type = 'Fiction'
            changed = True

    if not b.genre:
        for s in lower_subjects:
            if s in [g.lower() for g in KNOWN_GENRES]:
                b.genre = s.title()
                changed = True
                break
            
    if not b.sub_genre and subjects:
        preferred = next((s for s in subjects if 'fiction' not in s.lower() and 'non' not in s.lower()), None)
        if preferred:
            b.sub_genre = preferred
            changed = True
    
    if not b.publication_year:
        pub_year = ol_data.get('publication_year')
        if pub_year:
            b.publication_year = pub_year
            changed = True
    # Try setting cover if available from search result
    if not getattr(b, 'cover_url', None):
        cover_id = ol_data.get('cover_id')
        if cover_id:
            b.cover_url = OpenLibraryService.get_cover_url(cover_id=cover_id, size='L')
            changed = True
            
    if not b.openlibrary_id:
        ol_id = ol_data.get('openlibrary_id')
        if ol_id:
            b.openlibrary_id = ol_id
            changed = True
            
    if changed:
        print(f"  >> Updated book: type={b.book_type}, genre={b.genre}, sub_genre={b.sub_genre}, publication_year={b.publication_year}")
        
    return changed
class BookImportService:
    """Service for importing books from CSV files"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for fuzzy matching: lowercase, strip punctuation, normalize whitespace"""
        if not text:
            return ""
        # Lowercase
        normalized = text.lower()
        # Remove punctuation (keep only alphanumeric and spaces)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        # Normalize whitespace (collapse multiple spaces to single space, strip edges)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    @staticmethod
    def import_from_csv(csv_file, debug: bool = False) -> dict:
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
            if hasattr(csv_file, 'stream'):
                stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)    
                csv_reader = csv.DictReader(stream)
            else:
                csv_reader = csv.DictReader(csv_file, delimiter=',')
                
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
                try:
                    if 'title' not in row or 'author' not in row:
                        raise ValueError("Missing required 'title' or 'author' field")
                    
                    # Check if book already exists by title+author (fuzzy match)
                    title_raw = (row.get('title') or '').strip()
                    author_raw = (row.get('author') or '').strip()
                    
                    # Normalize for fuzzy matching
                    title_normalized = BookImportService.normalize_text(title_raw)
                    author_normalized = BookImportService.normalize_text(author_raw)
                    
                    # Query all books and check normalized versions
                    existing_book = None
                    if title_normalized and author_normalized:
                        all_books = Book.query.all()
                        for book in all_books:
                            if (BookImportService.normalize_text(book.title) == title_normalized and
                                BookImportService.normalize_text(book.author) == author_normalized):
                                existing_book = book
                                break
                    
                    if existing_book:
                        result['errors'].append(f"Row {row_num}: Book '{title_raw}' by '{author_raw}' already exists (matches '{existing_book.title}' by '{existing_book.author}')")
                        result['error_count'] += 1
                        if debug:
                            print(f"Debug: Skipping existing book '{title_raw}' by '{author_raw}'")
                        continue
                    
                    isbn = row.get('isbn', '').strip()
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
                        except Exception as e:
                            # Continue even if OpenLibrary lookup fails
                            print(f"OpenLibrary lookup failed for {isbn}: {e}")

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

                    else:
                        enrich_book_from_openlibrary(book)
                    
            
                    # Validate required fields
                    if not book.title:
                        result['errors'].append(f"Row {row_num}: Title is required")
                        result['error_count'] += 1
                        continue
                    
                    if not debug:
                        db.session.add(book)
                    else:
                        print(f"Debug: Would add book: {book}")
                    result['success_count'] += 1
                    
                except Exception as e:
                    if debug:
                        print(f"Debug: Error processing row {row_num}: {e}")
                        print(f"Row data: {row}")

                    result['errors'].append(f"Row {row_num}: {str(e)}")
                    result['error_count'] += 1

            if not debug:
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
