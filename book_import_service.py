import csv
import io
import re
from models import Book, db
from openlibrary_service import OpenLibraryService
from csv_cli import CSVBookRecord, select_best_work, WorkWrapper
import attrs

def book_to_csvbookrecord(b: Book) -> CSVBookRecord:
    """Convert a Book object to a CSV row dict"""
    fields = attrs.fields(CSVBookRecord)
    return CSVBookRecord(**{k.name: getattr(b, k.name) for k in fields})
    
    
def enrich_book_from_openlibrary(b: Book) -> bool:
    """Enrich a Book object with data from OpenLibrary."""
    record = book_to_csvbookrecord(b)
    if not record.enrichable():
        return False
        
    try:
        print("ABOUT TO SEARCH")
        results = OpenLibraryService.search_books(
            f"{b.title} {b.author}",
            fields=['key', 'title', 'subject', 'first_publish_year', 'cover_i'], 
            limit=1
        )
        print("DONE SEARCH")
        if not results:
            print(f"No OpenLibrary results found for '{b.title}' by {b.author}")
            return False
            
        ol_data = results[0]
    except Exception as e:
        print(f"OpenLibrary lookup failed for {b.author} {b.title}: {e}")
        return False

    print(f"Processing book: {b.title} by {b.author}.")
    
    record = record.update_from_openlibrary_work(
        WorkWrapper(ol_data, ask=False), quick=True
    )
    print(record)
    changed = False
    for k in attrs.fields(CSVBookRecord):
        old_value = getattr(b, k.name)
        new_value = getattr(record, k.name)
        if old_value != new_value:
            setattr(b, k.name, new_value)
            changed = True
    print("CHANGED?", changed)   
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
    def import_from_csv(csv_file, debug: bool = False, skip_enrichment: bool = False) -> dict:
        """
        Import books from CSV file
        Expected CSV format: title, author, book_type, genre, sub_genre, topic, lexile_rating, grade, owned
        
        Args:
            csv_file: File object or file handle
            debug: Print debug messages
            skip_enrichment: If True, skip OpenLibrary enrichment (faster)
        
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
                    
                    record = CSVBookRecord.from_dict(row)
                    if not skip_enrichment and record.enrichable():
                        works = OpenLibraryService.author_title_search(title=record.title, author=record.author, fields="all", limit=1)
                        work = select_best_work(works)
                        record.update_from_openlibrary_work(work, quick=True, ask=False)

                    book = Book(
                        title=record.title,
                        author=record.author,
                        book_type=record.book_type,
                        genre=record.genre,
                        sub_genre=record.sub_genre,
                        topic=record.topic,
                        lexile_rating=record.lexile_rating,
                        grade=record.grade,
                        owned=record.owned,
                        openlibrary_id=record.openlibrary_id,
                        description=record.description,
                        cover_url=record.cover_url,
                        publication_year=record.publication_year
                    )
                    # # Try to enrich from OpenLibrary if ISBN is provided
                    # if isbn:
                    #     try:
                    #         ol_data = OpenLibraryService.get_book_by_isbn(isbn)
                    #     except Exception as e:
                    #         # Continue even if OpenLibrary lookup fails
                    #         print(f"OpenLibrary lookup failed for {isbn}: {e}")

                    #     if ol_data:
                    #         if not book.title:
                    #             book.title = ol_data.get('title', '')
                    #         if not book.author:
                    #             book.author = ol_data.get('author', '')
                    #         book.openlibrary_id = ol_data.get('openlibrary_id', '')
                    #         book.description = ol_data.get('description', '')
                    #         book.cover_url = ol_data.get('cover_url', '')
                    #         book.publication_year = ol_data.get('publication_year')
                    #         # Don't override genre/topic from CSV if they exist
                    #         if not book.genre and ol_data.get('genre'):
                    #             book.genre = ol_data.get('genre', '')

                    # else:
                    #     enrich_book_from_openlibrary(book)
                    
                    if not debug:
                        try:
                            db.session.add(book)
                            db.session.flush()  # Check for constraint violations before commit
                            result['success_count'] += 1
                        except Exception as add_error:
                            db.session.rollback()
                            result['errors'].append(f"Row {row_num}: Failed to add book - {str(add_error)}")
                            result['error_count'] += 1
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
            ['title', 'author', 'book_type', 'genre', 'sub_genre', 'topic', 'lexile_rating', 'grade', 'owned'],
            ['The Hunger Games', 'Suzanne Collins', 'Fiction', 'Science Fiction', 'Dystopian', 'Courage', '810L', '7', 'Physical'],
            ['Wonder', 'R.J. Palacio', 'Fiction', 'Realistic Fiction', 'School Life', 'Kindness', '790L', '5', 'Kindle'],
            ['I Am Malala', 'Malala Yousafzai', 'Non-Fiction', 'Biography', 'Memoir', 'Activism', '1000L', '8', 'Not Owned']
        ]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(sample_data)
        return output.getvalue()
