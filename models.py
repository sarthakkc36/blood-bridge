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
    status = db.Column(db.String(20), default='completed')
    notes = db.Column(db.Text)

    # Relationships
    donor = db.relationship('User', backref='donations')