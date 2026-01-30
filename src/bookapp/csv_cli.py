"""Quick and easy CLI interface for updating CSV file info from openlibrary.org."""

import csv
import pickle
from typing import Literal, Self
from cyclopts import App
import attrs
from pathlib import Path
import questionary as qs
from rich.console import Console
from bookapp.openlibrary_service import OpenLibraryWork, OpenLibraryService
import re

cns = Console()
app = App()

def get_flask_app():
    """Lazy import to avoid circular dependency"""
    from bookapp.app import app as flask_app
    return flask_app

def get_genres_from_db(book_type: Literal['Fiction', 'Non-Fiction']) -> dict[str, list[str]]:
    """Get genres and sub-genres from the database for a given book type."""
    from bookapp.models import Genre
    flask_app = get_flask_app()
    with flask_app.app_context():
        genres = Genre.query.filter_by(book_type=book_type).all()
        result = {}
        for genre in genres:
            sub_genre_names = [sg.name for sg in genre.sub_genres]
            result[genre.name] = sub_genre_names
        return result

def get_topics_from_db() -> list[str]:
    """Get all topics from the database."""
    from bookapp.models import Topic
    flask_app = get_flask_app()
    with flask_app.app_context():
        topics = Topic.query.all()
        return [topic.name for topic in topics]

def get_genre_maps_from_db() -> dict[str, str]:
    """Get all genre mappings from the database."""
    from bookapp.models import GenreMap
    flask_app = get_flask_app()
    with flask_app.app_context():
        maps = GenreMap.query.all()
        return {m.alternative_name: m.canonical_name for m in maps}

def add_topic_to_db(topic_name: str):
    """Add a new topic to the database."""
    from bookapp.models import Topic, db
    flask_app = get_flask_app()
    with flask_app.app_context():
        # Check if already exists
        existing = Topic.query.filter_by(name=topic_name).first()
        if not existing:
            topic = Topic(name=topic_name)
            db.session.add(topic)
            db.session.commit()
            print(f"Added new topic to database: {topic_name}")

def get_best_bet_genres_from_subjects(subjects: list[str]) -> dict[str, str]:
    """Given a list of subjects, return the best book_type, genre, and sub_genre matches."""
    from bookapp.models import Genre

    book_type = None
    genre = None
    sub_genre = None

    lower_subjects = [s.lower() for s in subjects]

    if any('non-fiction' in s or 'nonfiction' in s or 'non fiction' in s for s in lower_subjects):
        book_type = 'Non-Fiction'
    elif 'fiction' in lower_subjects:
        book_type = 'Fiction'

    if book_type:
        known_genres = get_genres_from_db(book_type)
    else:
        known_genres = get_genres_from_db('Fiction') | get_genres_from_db('Non-Fiction')

    lower_known_genres = [g.lower() for g in known_genres.keys()]
    norm_map = dict(zip(lower_known_genres, known_genres.keys()))
    possible_genres = [
        norm_map[g]
        for g  in lower_subjects
        if g in lower_known_genres
    ]

    if possible_genres:
        genre = possible_genres[0]  # Take the first match

        # Now find sub-genre
        known_sub_genres = known_genres[genre]
        lower_known_sub_genres = [sg.lower() for sg in known_sub_genres]

        if possible_sub_genres := [
            known_sub_genres[idx]
            for idx, sg in enumerate(lower_known_sub_genres)
            if sg in lower_subjects
        ]:
            sub_genre = possible_sub_genres[0]  # Take the first match

    if book_type is None and genre is not None:
        book_type =  Genre.query.filter_by(name=genre).first().book_type

    return {'book_type': book_type, 'genre': genre, 'sub_genre': sub_genre}

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

@attrs.define
class WorkWrapper:
    work: OpenLibraryWork
    ask: bool = True

    def __getattr__(self, name: str):
        return getattr(self.work, name)
    
    def get_book_type(self) -> Literal['Fiction', 'Non-Fiction', None]:
        """Infer book type from subjects."""
        subjects = self.work.subject or []
        non_fiction_subjects = [s for s in subjects if 'non-fiction' in s.lower() or 'nonfiction' in s.lower() or 'non fiction' in s.lower()]
        
        out = 'Non-Fiction' if non_fiction_subjects else "Fiction" if any(s.lower() == 'fiction' for s in subjects) else None
        
        if out is None and self.ask:
            # Ask user to select
            out = qs.select(
                "Please select the book type:",
                choices=['Fiction', 'Non-Fiction']
            ).ask()
            
        return out

    def get_genre(self, book_type: Literal['Fiction', 'Non-Fiction'], top_genre: str | None = None) -> str | None:
        """Get genre from subjects."""
        known = get_genres_from_db(book_type)
        if top_genre:
            known = known[top_genre]  # get a sub-genre!
            
        subjects = self.work.subject or []
        genre_maps = get_genre_maps_from_db()
        lower_subjects = [normalize_text(s) for s in subjects]
        lower_genres = [normalize_text(g) for g in known]
        lower_subjects = [normalize_text(genre_maps.get(s, s)) for s in lower_subjects]
                
        if top_genre is None:
            known_names = list(known.keys())
        else:
            known_names = known
            
        possible_genres = [
            known_names[idx]
            for idx, s in enumerate(lower_genres)
            if s in lower_subjects
        ]

        if len(possible_genres) == 1:
            return possible_genres[0]

        # Otherwise, ask user to select
        if possible_genres and self.ask:
            selected = qs.select(
                "Multiple genres found. Please select the most appropriate one:",
                choices=possible_genres + ["None of these"]
            ).ask()

            if selected and selected != "None of these":
                return selected

            if selected == "None of these":
                # Ask the user to choose genre manually
                selected = qs.select(
                    "Please select the genre that best fits this book: {}",
                    choices=known_names + ["None of these"]
                ).ask() 
                if selected and selected != "None of these":
                    return selected
        return None
    
    
    def get_topic(self) -> str | None:
        """Get topic from subjects."""
        subjects = self.work.subjects or []
        known_topics = get_topics_from_db()
        lower_subjects = [s.lower() for s in subjects]
        lower_known_topics = [t.lower() for t in known_topics]
        possible_topics = []

        possible_topics.extend(
            subjects[idx]
            for idx, s in enumerate(lower_subjects)
            if s in lower_known_topics
        )
        # Go through and add all other subjects that are not already known topics
        possible_topics.extend(
            subj for subj in subjects if subj.lower() not in lower_known_topics
        )
        # Ask user to select
        if possible_topics and self.ask:
            topic = qs.select(
                "Please select the most appropriate one:", choices=possible_topics
            ).ask()
            add_topic_to_db(topic)
            return topic
        
        return None
                
@attrs.define
class CSVBookRecord:
    title: str = attrs.field(converter=str)
    author: str = attrs.field(converter=str)
    openlibrary_id: str | None = attrs.field(default=None)
    publication_year: int | None = attrs.field(default=None)
    cover_url: str | None = attrs.field(default=None)
    book_type: Literal['Fiction', 'Non-Fiction'] | None = attrs.field(default=None)
    sub_genre: str | None = attrs.field(default=None)
    genre: str | None = attrs.field(default=None)
    topic: str | None = attrs.field(default=None)
    lexile_rating: str | None = attrs.field(default=None)
    grade: int | None = attrs.field(default=None, converter=lambda x: int(x) if x not in (None, '') else None)
    owned: Literal['Physical', 'Kindle', 'Not Owned', 'Audible'] = attrs.field(default='Not Owned')
    description: str | None = attrs.field(default=None)
    
    @grade.validator
    def check_grade(self, attribute, value):
        if value is not None and (value < 1 or value > 12):
            raise ValueError("Grade must be between 1 and 12")
        
    def asdict(self) -> dict:
        return attrs.asdict(self)
    @classmethod
    def from_dict(cls, data: dict) -> Self:
        data = {k: v for k, v in data.items() if v not in (None, '')}
        return cls(**data)


    def enrichable(self) -> bool:
        """Determine if the record can be enriched (i.e. missing some data)."""
        return (
            self.book_type is None or
            self.genre is None or
            self.sub_genre is None or
            self.topic is None or
            self.publication_year is None or
            self.cover_url is None or
            self.description is None
        )
    
    @classmethod
    def from_openlibrary_id(cls, olid: str, ask: bool = False, quick: bool = True) -> Self:
        """Create a CSVBookRecord from an ID."""
        works = OpenLibraryService.search_books(query=olid, fields='all', limit=1)
        if not works:
            raise ValueError(f"No work found for OpenLibrary ID: {olid}")
        
        out = cls(title=works[0].title, author=works[0].author_name[0] if works[0].author_name else '')
        return out.update_from_openlibrary_work(WorkWrapper(works[0], ask=ask), quick=quick)
    
    def update_from_openlibrary_work(self, work: WorkWrapper, quick: bool = False) -> Self:
        """Update the record with data from an OpenLibrary work."""
        print("in update_from_openlibrary_work")
        if quick and not work.ask:
            genres = get_best_bet_genres_from_subjects(work.work.subject or [])
            book_type = genres['book_type']
            genre = genres['genre']
            sub_genre = genres['sub_genre']
        else:
            book_type = work.get_book_type()
            if book_type is not None:
                genre = work.get_genre(book_type=book_type)
                sub_genre = work.get_genre(book_type=book_type, top_genre=genre) if genre else None
            else:
                genre = None
                sub_genre = None
            
        print(f"book_type={book_type}, genre={genre}, sub_genre={sub_genre}")
        topic = work.get_topic()
        olid = work.work.olid
        description = work.work.description
        cover_url = f"https://covers.openlibrary.org/b/id/{work.work.cover_i}-L.jpg"
        publication_year = work.work.first_publish_year

        print(f"topic={topic}, olid={olid}, description={description}, cover_url={cover_url}, publication_year={publication_year}")
        
        # Check one last time if this should be accepted
        if not quick:
            confirm = qs.confirm(
                f"Apply these updates to '{self.title}' by '{self.author}'?", default=True
            ).ask()
            if not confirm:
                return self
        
        print("Applying updates...")
        return attrs.evolve(
            self,
            openlibrary_id=olid or self.openlibrary_id,
            description=description or self.description,
            cover_url=cover_url or self.cover_url,
            publication_year=publication_year or self.publication_year,
            book_type=book_type or self.book_type,
            genre=genre or self.genre,
            sub_genre=sub_genre or self.sub_genre,
            topic=topic or self.topic,
        )
    
def select_best_work(works: list):
    """Select the best matching work from a list based on title and author."""
    if not works:
        return None
    
    if len(works) == 1:
        return works[0]
    
    # # Simple heuristic: prefer works with matching title and author
    # for work in works:
    #     if (work.title.lower() == record.title.lower() and
    #         any(author.lower() in record.author.lower() for author in work.authors)):
    #         return work

    # Otherwise, ask the user to select
    choices = [f"{work.title} by {work.author_name[0]} (https://openlibrary.org{work.key})" for work in works]
    selected = qs.select(
        "Multiple works found. Please select the best match:",
        choices=choices + ["None of these"]
    ).ask()
    
    if selected and selected != "None of these":
        index = choices.index(selected)
        return works[index]
        
    # Get the ID from the user
    work_id = qs.text(
        "Please enter the OpenLibrary ID of the correct work (or leave blank to skip):"
    ).ask()
    
    if work_id:
        works = OpenLibraryService.search_books(query=work_id, fields='all', limit=1)
        return select_best_work(works)
    return None

def enrich_csv_record(csv_record: dict, force: bool = False, quick: bool = False, ask: bool = True) -> CSVBookRecord:
    """Enrich a single CSV book record using OpenLibrary data."""
    record = CSVBookRecord.from_dict(csv_record)
    
    cns.print(f"> Enriching [bold blue]{record.title}[/] by [bold orange]{record.author}[/]")
    
    if not record.enrichable() and not force:
        cns.print("  [green] :checkmark: No enrichment needed.[/]")
        return record  # No enrichment needed
        
    works = OpenLibraryService.author_title_search(title=record.title, author=record.author, fields="all", limit=1)
    work = select_best_work(works)
    if work is None:
        cns.print("  [red] :crossmark: No matching work found, skipping.[/]")
        return record  # No matching work found

    work = WorkWrapper(work, ask=ask)
    
    urls = [
        f"https://openlibrary.org{work.olid}",
    ]
    # if 'librarything' in work.work.identifiers:
    #     urls += [f"https://www.librarything.com/work/{lt_id}" for lt_id in work.work.identifiers['librarything']]
        
    cns.print(f"  [yellow]:book: Found work [bold]{work.work.title}[/]: {' | '.join(urls)}[/]")
    return record.update_from_openlibrary_work(work, quick=quick)

@app.command()
def enrich(
    input_csv: Path,
    output_csv: Path,
    cache_path: Path = Path("cache.pickle"),
    force: bool = False,
    quick: bool = False
):
    """Enrich book records in a CSV file using OpenLibrary data."""
    records = []
    
    if cache_path.exists():
        cns.print(f"[blue]:inbox_tray: Loading cached data from {cache_path}[/]")
        with open(cache_path, "rb") as cachefile:
            records = pickle.load(cachefile)
            
    with (
        open(input_csv, newline='', encoding='utf-8') as csvfile,
    ):
        
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if i < len(records):
                cns.print(f"[blue]:inbox_tray: Using cached record {i+1}[/]")
                continue  # Already processed
            
            enriched_record = enrich_csv_record(row, force=force, quick=quick)
            records.append(attrs.asdict(enriched_record))
    
            with open(cache_path, "wb") as cachefile:
                pickle.dump(records, cachefile)
            
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = records[0].keys() if records else []
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    print(f"Enriched data written to {output_csv}")
    
if __name__ == "__main__":
    app()