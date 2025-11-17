import requests
from typing import Optional, Dict, Any

class OpenLibraryService:
    """Service for interacting with OpenLibrary API"""
    
    BASE_URL = "https://openlibrary.org"
    
    @staticmethod
    def search_books(query: str, fields: list[str] = (), limit: int = 10) -> list:
        """Search for books by title, author, or ISBN"""
        try:
            url = f"{OpenLibraryService.BASE_URL}/search.json"
            params = {
                'q': query,
                'limit': limit,
                'fields': ','.join(fields) if fields else None
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            books = []
            for doc in data.get('docs', []):
                book = {
                    'title': doc.get('title', ''),
                    'author': ', '.join(doc.get('author_name', [])),
                    'isbn': doc.get('isbn', [''])[0] if doc.get('isbn') else '',
                    'openlibrary_id': doc.get('key', ''),
                    'cover_id': doc.get('cover_i'),
                    'publication_year': doc.get('first_publish_year'),
                    "subjects": doc.get('subject', [])
                }
                books.append(book)
            
            return books
        except Exception as e:
            print(f"Error searching OpenLibrary: {e}")
            return []
    
    @staticmethod
    def get_book_by_isbn(isbn: str) -> Optional[Dict[str, Any]]:
        """Get book details by ISBN"""
        try:
            url = f"{OpenLibraryService.BASE_URL}/isbn/{isbn}.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Get work details for more info
            work_key = None
            if 'works' in data and len(data['works']) > 0:
                work_key = data['works'][0]['key']
            
            book = {
                'title': data.get('title', ''),
                'openlibrary_id': data.get('key', ''),
                'isbn': isbn,
                'publication_year': data.get('publish_date', ''),
                'publisher': ', '.join(data.get('publishers', [])) if data.get('publishers') else ''
            }
            
            # Get author information
            if 'authors' in data and len(data['authors']) > 0:
                author_key = data['authors'][0]['key']
                author_data = OpenLibraryService.get_author(author_key)
                book['author'] = author_data.get('name', '') if author_data else ''
            
            # Get additional details from work
            if work_key:
                work_data = OpenLibraryService.get_work(work_key)
                if work_data:
                    book['description'] = work_data.get('description', '')
                    if isinstance(book['description'], dict):
                        book['description'] = book['description'].get('value', '')
                    subjects = work_data.get('subject', []) or []
                    # keep original behavior
                    book['genre'] = ', '.join(subjects[:3]) if subjects else ''
                    # also provide raw subjects for downstream inference
                    book['subjects'] = subjects
            
            # Get cover URL
            if 'covers' in data and len(data['covers']) > 0:
                cover_id = data['covers'][0]
                book['cover_url'] = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
            
            return book
        except Exception as e:
            print(f"Error getting book by ISBN: {e}")
            return None
    
    @staticmethod
    def get_work(work_key: str) -> Optional[Dict[str, Any]]:
        """Get work details from OpenLibrary"""
        try:
            url = f"{OpenLibraryService.BASE_URL}{work_key}.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting work: {e}")
            return None
    
    @staticmethod
    def get_author(author_key: str) -> Optional[Dict[str, Any]]:
        """Get author details from OpenLibrary"""
        try:
            url = f"{OpenLibraryService.BASE_URL}{author_key}.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting author: {e}")
            return None
    
    @staticmethod
    def get_cover_url(isbn: str = None, cover_id: int = None, size: str = 'M') -> str:
        """
        Get cover image URL
        size: S (small), M (medium), L (large)
        """
        if isbn:
            return f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"
        elif cover_id:
            return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"
        return ""
