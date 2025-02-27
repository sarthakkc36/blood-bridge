from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def create_admin():
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@bloodbank.com').first()
        if not admin:
            admin = User(
                email='admin@bloodbank.com',
                first_name='Admin',
                last_name='User',
                password_hash=generate_password_hash('adminpass123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")

if __name__ == '__main__':
    create_admin()