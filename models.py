from extensions import db
from flask_login import UserMixin
from datetime import datetime
import pyotp

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False, default='donor')
    # Additional profile fields
    blood_type = db.Column(db.String(5))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    medical_conditions = db.Column(db.Text)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 2FA fields
    totp_secret = db.Column(db.String(32))
    totp_enabled = db.Column(db.Boolean, default=False)
    
    # Donor verification fields
    is_verified = db.Column(db.Boolean, default=False)
    verification_status = db.Column(db.String(20), default='unverified')  # 'unverified', 'pending', 'approved', 'rejected'
    verification_date = db.Column(db.DateTime)
    last_donation_date = db.Column(db.DateTime)
    next_eligible_date = db.Column(db.DateTime)
    verification_note = db.Column(db.Text)

    def get_totp_uri(self):
        """Generate the TOTP URI for QR code generation"""
        if self.totp_secret:
            return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
                name=self.email,
                issuer_name="Blood Donation System"
            )
        return None

    def verify_totp(self, token):
        """Verify the TOTP token"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token)

    def generate_totp_secret(self):
        """Generate a new TOTP secret"""
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret
        
    def can_donate(self):
        """Check if user is eligible to donate based on verification and last donation date"""
        if not self.is_verified or self.verification_status != 'approved':
            return False, "You need to complete the verification process before donating."
            
        if self.next_eligible_date and self.next_eligible_date > datetime.utcnow():
            return False, f"You are not eligible to donate until {self.next_eligible_date.strftime('%Y-%m-%d')}."
            
        return True, "You are eligible to donate blood."
        
    def get_full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"


class BloodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    units_needed = db.Column(db.Integer, nullable=False, default=1)
    urgency = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    hospital = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    required_by = db.Column(db.DateTime)

    # Relationships
    requester = db.relationship('User', backref='blood_requests')


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    donation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    units = db.Column(db.Integer, nullable=False, default=1)
    center = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'cancelled'
    notes = db.Column(db.Text)

    # Relationships
    donor = db.relationship('User', backref='donations')


class DonorVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    id_document_filename = db.Column(db.String(200))
    medical_certificate_filename = db.Column(db.String(200))
    address_proof_filename = db.Column(db.String(200))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    review_date = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    
    # Health questionnaire responses stored as JSON
    questionnaire_responses = db.Column(db.Text)  # Stored as JSON
    
    # Relationships
    donor = db.relationship('User', foreign_keys=[donor_id], backref='verifications')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
import secrets
from datetime import datetime, timedelta

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    # Relationship
    user = db.relationship('User', backref='password_resets')
    
    def __init__(self, user_id, expires_in=24):
        """
        Initialize a new password reset token
        
        Args:
            user_id: The ID of the user requesting the password reset
            expires_in: Hours until the token expires (default: 24)
        """
        self.user_id = user_id
        self.token = secrets.token_urlsafe(64)
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=expires_in)
        self.used = False
    
    def is_valid(self):
        """Check if the token is valid (not expired and not used)"""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def invalidate(self):
        """Mark the token as used"""
        self.used = True

# Add these methods to the User class

def generate_password_reset_token(self):
    """Generate a new password reset token for the user"""
    # Invalidate any existing tokens
    for token in self.password_resets:
        if not token.used and datetime.utcnow() < token.expires_at:
            token.invalidate()
    
    # Create a new token
    reset = PasswordReset(user_id=self.id)
    db.session.add(reset)
    db.session.commit()
    return reset.token

def verify_password_reset_token(self, token):
    """Verify if a given token is valid for this user"""
    reset = PasswordReset.query.filter_by(user_id=self.id, token=token, used=False).first()
    if reset and reset.is_valid():
        return reset
    return None