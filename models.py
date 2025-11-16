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
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    isbn = db.Column(db.String(13), unique=True)
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
