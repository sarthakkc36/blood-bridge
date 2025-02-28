import re
from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

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

def generate_request_id():
    """Generate a unique request ID for blood requests."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f'REQ{timestamp}'

def calculate_urgency_level(request_data):
    """
    Calculate urgency level based on various factors.
    Returns: 'high', 'medium', or 'low'
    """
    factors = {
        'emergency': 10,
        'surgery_scheduled': 5,
        'low_stock': 3,
        'regular': 1
    }
    
    score = factors.get(request_data.get('type', 'regular'), 1)
    
    if request_data.get('quantity', 1) > 3:
        score += 2
        
    if score >= 8:
        return 'high'
    elif score >= 4:
        return 'medium'
    return 'low'

def get_blood_stock_status():
    """
    Get current blood stock status.
    Returns dictionary with blood types and their availability status.
    """
    return {
        'A+': {'units': 65, 'status': 'normal'},
        'A-': {'units': 45, 'status': 'normal'},
        'B+': {'units': 75, 'status': 'normal'},
        'B-': {'units': 35, 'status': 'warning'},
        'AB+': {'units': 25, 'status': 'warning'},
        'AB-': {'units': 15, 'status': 'critical'},
        'O+': {'units': 85, 'status': 'normal'},
        'O-': {'units': 55, 'status': 'normal'}
    }

def check_donor_eligibility(donor):
    """
    Check if a donor is eligible to donate blood based on verification status and last donation date.
    
    Returns:
        tuple: (is_eligible, message)
    """
    if not donor.is_verified:
        return False, "You need to be verified before you can donate."
    
    if donor.verification_status != 'approved':
        return False, f"Your verification status is '{donor.verification_status}'. You need to be approved to donate."
    
    if donor.next_eligible_date and donor.next_eligible_date > datetime.utcnow():
        days_remaining = (donor.next_eligible_date - datetime.utcnow()).days
        return False, f"You will be eligible to donate again in {days_remaining} days."
    
    return True, "You are eligible to donate blood."

def format_verification_status(status):
    """Format verification status for display with appropriate color class."""
    status_formats = {
        'unverified': {'text': 'Not Verified', 'class': 'secondary'},
        'pending': {'text': 'Pending Review', 'class': 'warning'},
        'approved': {'text': 'Verified', 'class': 'success'},
        'rejected': {'text': 'Rejected', 'class': 'danger'}
    }
    
    return status_formats.get(status, {'text': status.capitalize(), 'class': 'secondary'})