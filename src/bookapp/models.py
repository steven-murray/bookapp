from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association table for many-to-many relationship between classes and students
class_students = db.Table('class_students',
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Association table for assigned reading lists
assigned_reading = db.Table('assigned_reading',
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True),
    db.Column('assigned_date', db.DateTime, default=datetime.utcnow)
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'admin' or 'student'
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    classes_enrolled = db.relationship('Class', secondary=class_students, 
                                      back_populates='students')
    reading_list = db.relationship('ReadingListItem', back_populates='user', 
                                   cascade='all, delete-orphan')
    books_read = db.relationship('BookRead', back_populates='user', 
                                cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='user', 
                             cascade='all, delete-orphan')
    suggested_books = db.relationship('SuggestedBook', 
                                     foreign_keys='SuggestedBook.student_id',
                                     back_populates='student',
                                     cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'


class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher = db.relationship('User', foreign_keys=[teacher_id])
    students = db.relationship('User', secondary=class_students, 
                              back_populates='classes_enrolled')
    assigned_books = db.relationship('Book', secondary=assigned_reading)
    
    def __repr__(self):
        return f'<Class {self.name}>'


class Book(db.Model):
    __table_args__ = (
        db.UniqueConstraint('author', 'title', name='uq_author_title'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    openlibrary_id = db.Column(db.String(50))
    # New metadata
    book_type = db.Column(db.String(20))  # 'Fiction' or 'Non-Fiction'
    sub_genre = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    topic = db.Column(db.String(100))
    lexile_rating = db.Column(db.String(20))
    grade = db.Column(db.Integer)  # Intended grade level (1-12)
    owned = db.Column(db.String(20), default='Not Owned')  # 'Physical', 'Kindle', 'Not Owned'
    description = db.Column(db.Text)
    cover_url = db.Column(db.String(500))
    publication_year = db.Column(db.Integer)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reading_list_items = db.relationship('ReadingListItem', back_populates='book',
                                        cascade='all, delete-orphan')
    books_read = db.relationship('BookRead', back_populates='book',
                                cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='book',
                             cascade='all, delete-orphan')
    
    def has_reviews(self):
        """Check if this book has any student reviews"""
        return len(self.reviews) > 0
    
    def __repr__(self):
        return f'<Book {self.title}>'


class ReadingListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='reading_list')
    book = db.relationship('Book', back_populates='reading_list_items')
    
    def __repr__(self):
        return f'<ReadingListItem User:{self.user_id} Book:{self.book_id}>'


class BookRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='books_read')
    book = db.relationship('Book', back_populates='books_read')
    
    def __repr__(self):
        return f'<BookRead User:{self.user_id} Book:{self.book_id}>'


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    # Guided review questions
    what_liked = db.Column(db.Text)  # What did you like about this book?
    what_learned = db.Column(db.Text)  # What did you learn?
    recommend_to = db.Column(db.Text)  # Who would you recommend this to?
    favorite_part = db.Column(db.Text)  # What was your favorite part?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='reviews')
    book = db.relationship('Book', back_populates='reviews')
    
    def __repr__(self):
        return f'<Review User:{self.user_id} Book:{self.book_id} Rating:{self.rating}>'


class SuggestedBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    suggested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text)  # Why this book is suggested
    suggested_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_accepted = db.Column(db.Boolean, default=False)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], 
                             back_populates='suggested_books')
    book = db.relationship('Book')
    suggested_by = db.relationship('User', foreign_keys=[suggested_by_id])
    
    def __repr__(self):
        return f'<SuggestedBook Student:{self.student_id} Book:{self.book_id}>'


class BookSuggestion(db.Model):
    """Students suggesting new books to be added to the library"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.Text)  # Why the student wants this book
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'added'
    suggested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    admin_notes = db.Column(db.Text)  # Admin's notes on the suggestion
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))  # Set when book is added to library
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])
    book = db.relationship('Book')
    
    def __repr__(self):
        return f'<BookSuggestion "{self.title}" by {self.author} from Student:{self.student_id}>'


class BookEditSuggestion(db.Model):
    """Students suggesting edits to existing books"""
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Suggested changes (NULL means no change suggested)
    suggested_title = db.Column(db.String(200))
    suggested_author = db.Column(db.String(200))
    suggested_openlibrary_id = db.Column(db.String(50))
    suggested_publication_year = db.Column(db.Integer)
    suggested_book_type = db.Column(db.String(20))
    suggested_genre = db.Column(db.String(100))
    suggested_sub_genre = db.Column(db.String(100))
    suggested_topic = db.Column(db.String(100))
    suggested_lexile_rating = db.Column(db.String(20))
    suggested_grade = db.Column(db.Integer)
    suggested_description = db.Column(db.Text)
    
    reason = db.Column(db.Text)  # Why the student is suggesting these changes
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    suggested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    admin_notes = db.Column(db.Text)
    
    # Relationships
    book = db.relationship('Book')
    student = db.relationship('User', foreign_keys=[student_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])
    
    def __repr__(self):
        return f'<BookEditSuggestion for Book:{self.book_id} from Student:{self.student_id}>'


class Genre(db.Model):
    """Allowed genres organized by book type (Fiction/Non-Fiction)"""
    id = db.Column(db.Integer, primary_key=True)
    book_type = db.Column(db.String(20), nullable=False)  # 'Fiction' or 'Non-Fiction'
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    sub_genres = db.relationship('SubGenre', back_populates='genre', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('book_type', 'name', name='uq_book_type_genre'),
    )
    
    def __repr__(self):
        return f'<Genre {self.book_type}:{self.name}>'


class SubGenre(db.Model):
    """Allowed sub-genres for each genre"""
    id = db.Column(db.Integer, primary_key=True)
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    genre = db.relationship('Genre', back_populates='sub_genres')
    
    __table_args__ = (
        db.UniqueConstraint('genre_id', 'name', name='uq_genre_subgenre'),
    )
    
    def __repr__(self):
        return f'<SubGenre {self.name}>'


class Topic(db.Model):
    """Allowed topics for books"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Topic {self.name}>'


class GenreMap(db.Model):
    """Mappings from alternative genre names to canonical genre names"""
    id = db.Column(db.Integer, primary_key=True)
    alternative_name = db.Column(db.String(100), nullable=False, unique=True)
    canonical_name = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<GenreMap {self.alternative_name} -> {self.canonical_name}>'
