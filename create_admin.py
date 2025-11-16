"""
Helper script to create an admin user
"""
from app import app, db
from models import User

def create_admin():
    with app.app_context():
        print("Create Admin User")
        print("-" * 40)
        
        username = input("Username: ")
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"Error: Username '{username}' already exists!")
            return
        
        email = input("Email: ")
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            print(f"Error: Email '{email}' already registered!")
            return
        
        first_name = input("First Name: ")
        last_name = input("Last Name: ")
        password = input("Password: ")
        
        # Create admin user
        admin = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='admin'
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print("\n" + "=" * 40)
        print(f"✓ Admin user '{username}' created successfully!")
        print("=" * 40)

if __name__ == '__main__':
    create_admin()
