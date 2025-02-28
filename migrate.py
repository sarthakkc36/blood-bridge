"""
Database Reset Script for the BloodBridge System

WARNING: This script will delete ALL existing data in the database
and recreate the tables from scratch. Only use this if you're setting up
a new system or don't mind losing your existing data.
"""

import sys
import logging
import os
from app import app, db

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_database():
    """Drop all tables and recreate them"""
    with app.app_context():
        try:
            logger.info("Dropping all existing tables...")
            db.drop_all()
            logger.info("All tables dropped successfully.")
            
            logger.info("Creating tables with new schema...")
            db.create_all()
            logger.info("All tables created successfully.")
            
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            return False

def create_upload_directories():
    """Create directories for uploaded verification documents"""
    upload_folder = os.path.join(app.root_path, 'static/uploads')
    subdirs = ['id_documents', 'medical_certificates', 'address_proofs']
    
    for subdir in subdirs:
        directory = os.path.join(upload_folder, subdir)
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
            else:
                logger.info(f"Directory already exists: {directory}")
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {str(e)}")
            return False
    
    return True

def setup_admin_account():
    """Create an admin account"""
    from werkzeug.security import generate_password_hash
    from models import User
    
    with app.app_context():
        try:
            # Check if admin already exists
            from models import User
            existing_admin = User.query.filter_by(email='admin@bloodbank.com').first()
            
            if existing_admin:
                logger.info("Admin account already exists.")
                return True
            
            # Create admin user
            admin = User(
                email='admin@bloodbank.com',
                first_name='Admin',
                last_name='User',
                password_hash=generate_password_hash('adminpass123'),
                role='admin',
                is_verified=True,
                verification_status='approved'
            )
            
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin account created successfully.")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating admin account: {str(e)}")
            return False

if __name__ == "__main__":
    print("BloodBridge Database Reset Tool")
    print("===============================")
    print("⚠️  WARNING: This will DELETE ALL DATA in your database and recreate the tables!")
    print("⚠️  Only proceed if you understand the consequences.")
    print()
    print("This script will:")
    print("1. Drop all existing tables")
    print("2. Create new tables with the donor verification schema")
    print("3. Set up upload directories")
    print("4. Create an admin account (admin@bloodbank.com / adminpass123)")
    print()
    
    confirm = input("Are you ABSOLUTELY SURE you want to continue? Type 'YES' to confirm: ")
    if confirm != 'YES':
        print("Database reset cancelled.")
        sys.exit(0)
    
    print("Starting database reset...")
    
    # Create upload directories
    if not create_upload_directories():
        logger.error("Failed to create upload directories.")
        sys.exit(1)
    
    # Reset database
    if not reset_database():
        logger.error("Failed to reset database.")
        sys.exit(1)
    
    # Create admin account
    if not setup_admin_account():
        logger.error("Failed to create admin account.")
        sys.exit(1)
    
    print("Database reset completed successfully!")
    print("You can now log in with the following admin credentials:")
    print("Email: admin@bloodbank.com")
    print("Password: adminpass123")