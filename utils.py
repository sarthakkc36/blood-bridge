import re
from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
import json

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """
    Validate password strength.
    Must be at least 8 characters long and contain:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def validate_password_complexity(password):
    """
    Validate password complexity.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def admin_required(f):
    """Decorator to require admin role for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def donor_required(f):
    """Decorator to require donor role for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'donor':
            flash('You need to be a donor to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def receiver_required(f):
    """Decorator to require receiver role for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'receiver':
            flash('You need to be a receiver to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def format_datetime(dt):
    """Format datetime for display."""
    return dt.strftime("%B %d, %Y %I:%M %p")

def calculate_next_donation_date(last_donation_date):
    """Calculate when user can donate again (56 days after last donation)."""
    return last_donation_date + timedelta(days=56)

def calculate_blood_compatibility(blood_type):
    """
    Returns a list of compatible blood types for a given blood type.
    """
    compatibility = {
        'A+': ['A+', 'AB+'],
        'A-': ['A+', 'A-', 'AB+', 'AB-'],
        'B+': ['B+', 'AB+'],
        'B-': ['B+', 'B-', 'AB+', 'AB-'],
        'AB+': ['AB+'],
        'AB-': ['AB+', 'AB-'],
        'O+': ['A+', 'B+', 'AB+', 'O+'],
        'O-': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    }
    return compatibility.get(blood_type, [])

def sanitize_input(text):
    """Sanitize user input to prevent XSS."""
    return re.sub(r'[<>]', '', text)

def log_admin_action(admin_user, action_type, target_user=None, details=None):
    """
    Log administrative actions for auditing purposes.
    
    Args:
        admin_user (User): The admin performing the action
        action_type (str): Type of action (e.g., 'password_reset', 'user_delete')
        target_user (User, optional): User the action was performed on
        details (dict, optional): Additional details about the action
    """
    try:
        from models import AdminActionLog
        from extensions import db

        log_entry = AdminActionLog(
            admin_id=admin_user.id,
            action_type=action_type,
            target_user_id=target_user.id if target_user else None,
            details=json.dumps(details) if details else None,
            timestamp=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        import logging
        logging.error(f"Error logging admin action: {str(e)}")
        db.session.rollback()

def format_verification_status(status):
    """Format verification status for display with appropriate color class."""
    status_formats = {
        'unverified': {'text': 'Not Verified', 'class': 'secondary'},
        'pending': {'text': 'Pending Review', 'class': 'warning'},
        'approved': {'text': 'Verified', 'class': 'success'},
        'rejected': {'text': 'Rejected', 'class': 'danger'}
    }
    
    return status_formats.get(status, {'text': status.capitalize(), 'class': 'secondary'})