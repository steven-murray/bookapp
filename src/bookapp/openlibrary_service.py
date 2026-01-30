import requests
from typing import Any
import attrs

@attrs.define
class OpenLibraryWork:
    """Data class representing an OpenLibrary Work
    
    See:
    https://github.com/internetarchive/openlibrary/blob/b4afa14b0981ae1785c26c71908af99b879fa975/openlibrary/plugins/worksearch/schemes/works.py#L38-L91
    """
    key: str
    title: str
    subjects: list[str] | None = None
    description: str | None = None
    
    subtitle: str | None = None
    alternative_title: str | None = None
    alternative_subtitle: str | None = None
    cover_i: int | None = None
    ebook_access: str | None = None
    edition_count: int | None = None
    edition_key: list[str] | None = None
    format: list[str] | None = None
    publish_date: list[str] | None = None
    lccn: list[str] | None = None
    ia: list[str] | None = None
    oclc: list[str] | None = None
    isbn: list[str] | None = None
    contributor: list[str] | None = None
    publish_place: list[str] | None = None
    publisher: list[str] | None = None
    author_key: list[str] | None = None
    author_name: list[str] | None = None
    author_alternative_name: list[str] | None = None
    subject: list[str] | None = None
    has_fulltext: bool | None = None
    title_suggest: str | None = None
    publish_year: list[int] | None = None
    language: list[str] | None = None
    first_publish_year: int | None = None
    lcc: list[str] | None = None
    ddc: list[str] | None = None
    
    @property
    def olid(self):
        return self.key
class OpenLibraryService:
    """Service for interacting with OpenLibrary API"""
    
    BASE_URL = "https://openlibrary.org"
    
    @staticmethod
    def author_title_search(
        title: str | None, 
        author: str | None = None,
        fields: str | tuple[str] = (),
        limit: int = 10
    ) -> list[OpenLibraryWork]:
        query = f"title:{title}" if title else ""
        if author:
            query += f" author:{author}"
        return OpenLibraryService.search_books(query=query, fields=fields, limit=limit)

    @staticmethod
    def search_books(
        query: str, 
        fields: str | tuple[str] = (), 
        limit: int = 10
    ) -> list[OpenLibraryWork]:
        """Search for books with arbitrary query string.
        """
        if not fields:
            fields = None
        elif fields == "all":
            fields = [field.name for field in attrs.fields(OpenLibraryWork)]

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

            # Remove any keys that aren't in OpenLibraryWork
            valid_keys = {field.name for field in attrs.fields(OpenLibraryWork)}
            filtered_docs = [
                {k: v for k, v in doc.items() if k in valid_keys}
                for doc in data.get('docs', [])
            ]
            return [OpenLibraryWork(**doc) for doc in filtered_docs]
        except Exception as e:
            print(f"Error searching OpenLibrary: {e}")
            return []
    
    @staticmethod
    def get_book_by_isbn(isbn: str) -> dict[str, Any] | None:
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
    def get_work(work_key: str) -> dict[str, Any] | None:
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
    def get_author(author_key: str) -> dict[str, Any] | None:
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
