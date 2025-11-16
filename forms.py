from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('student', 'Student'), ('admin', 'Administrator')], 
                      validators=[DataRequired()])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class ClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    author = StringField('Author', validators=[Optional(), Length(max=200)])
    isbn = StringField('ISBN', validators=[Optional(), Length(max=13)])
    book_type = SelectField('Type', choices=[('', 'Select Type'), ('Fiction', 'Fiction'), ('Non-Fiction', 'Non-Fiction')], validators=[Optional()])
    sub_genre = StringField('Sub-genre', validators=[Optional(), Length(max=100)])
    genre = StringField('Genre', validators=[Optional(), Length(max=100)])
    topic = StringField('Topic', validators=[Optional(), Length(max=100)])
    lexile_rating = StringField('Lexile Rating', validators=[Optional(), Length(max=20)])
    grade = IntegerField('Grade', validators=[Optional(), NumberRange(min=1, max=12, message='Grade must be between 1 and 12')])
    owned = SelectField('Owned', choices=[('Not Owned', 'Not Owned'), ('Physical', 'Physical'), ('Kindle', 'Kindle')], default='Not Owned', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])

class CSVUploadForm(FlaskForm):
    csv_file = FileField('CSV File', validators=[
        DataRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])

class ReviewForm(FlaskForm):
    rating = IntegerField('Rating (1-5 stars)', validators=[
        DataRequired(),
        NumberRange(min=1, max=5, message='Rating must be between 1 and 5')
    ])
    what_liked = TextAreaField('What did you like about this book?', validators=[Optional()])
    what_learned = TextAreaField('What did you learn?', validators=[Optional()])
    recommend_to = TextAreaField('Who would you recommend this book to?', validators=[Optional()])
    favorite_part = TextAreaField('What was your favorite part?', validators=[Optional()])

class SuggestBookForm(FlaskForm):
    book_id = HiddenField('Book ID', validators=[DataRequired()])
    reason = TextAreaField('Why are you suggesting this book?', validators=[Optional()])

class SearchBookForm(FlaskForm):
    query = StringField('Search Books', validators=[DataRequired()])


class StudentBookFilterForm(FlaskForm):
    class Meta:
        csrf = False  # GET-only filter form; no state changes

    book_type = SelectField(
        'Type', choices=[('', 'Any'), ('Fiction', 'Fiction'), ('Non-Fiction', 'Non-Fiction')], validators=[Optional()]
    )
    genre = SelectField('Genre', choices=[('', 'Any')], validators=[Optional()])
    sub_genre = SelectField('Sub-genre', choices=[('', 'Any')], validators=[Optional()])
    min_grade = IntegerField('Min Grade', validators=[Optional(), NumberRange(min=1, max=12)])
    max_grade = IntegerField('Max Grade', validators=[Optional(), NumberRange(min=1, max=12)])
    owned = SelectField('Owned', choices=[('', 'Any'), ('Physical', 'Physical'), ('Kindle', 'Kindle'), ('Not Owned', 'Not Owned')], validators=[Optional()])
    search = StringField('Search', validators=[Optional(), Length(max=200)])
