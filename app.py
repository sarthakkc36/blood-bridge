import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime
import qrcode
import io
import base64
from extensions import db
from models import User, BloodRequest, Donation

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_123")
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:Ss%40071424@localhost:5432/bloodbridge"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            if user.totp_enabled:
                # Store user ID in session for 2FA verification
                session['pending_user_id'] = user.id
                return redirect(url_for('verify_2fa'))
            login_user(user)
            return redirect(get_dashboard_route(user.role))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'pending_user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['pending_user_id'])
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        token = request.form.get('token')
        if user.verify_totp(token):
            login_user(user)
            session.pop('pending_user_id', None)
            return redirect(get_dashboard_route(user.role))
        flash('Invalid 2FA code')

    return render_template('verify_2fa.html')

@app.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if not current_user.totp_secret:
        current_user.generate_totp_secret()
        db.session.commit()

    if request.method == 'POST':
        token = request.form.get('token')
        if current_user.verify_totp(token):
            current_user.totp_enabled = True
            db.session.commit()
            flash('Two-factor authentication has been enabled')
            return redirect(url_for('profile'))
        flash('Invalid 2FA code')

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(current_user.get_totp_uri())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert QR code to base64 for displaying in template
    buffered = io.BytesIO()
    img.save(buffered)
    qr_code = base64.b64encode(buffered.getvalue()).decode()

    return render_template('setup_2fa.html', 
                         qr_code=f"data:image/png;base64,{qr_code}",
                         secret=current_user.totp_secret)

@app.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.session.commit()
    flash('Two-factor authentication has been disabled')
    return redirect(url_for('profile'))

def get_dashboard_route(role):
    return {
        'admin': url_for('admin_dashboard'),
        'donor': url_for('donor_dashboard'),
        'receiver': url_for('receiver_dashboard')
    }.get(role, url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    blood_requests = BloodRequest.query.order_by(BloodRequest.created_at.desc()).limit(5).all()
    donations = Donation.query.order_by(Donation.donation_date.desc()).limit(5).all()
    return render_template('admin_dashboard.html', blood_requests=blood_requests, donations=donations)

@app.route('/donor')
@login_required
def donor_dashboard():
    if current_user.role != 'donor':
        return redirect(url_for('index'))
    donations = Donation.query.filter_by(donor_id=current_user.id).order_by(Donation.donation_date.desc()).all()
    return render_template('donor_dashboard.html', donations=donations)

@app.route('/receiver')
@login_required
def receiver_dashboard():
    if current_user.role != 'receiver':
        return redirect(url_for('index'))
    requests = BloodRequest.query.filter_by(requester_id=current_user.id).order_by(BloodRequest.created_at.desc()).all()
    return render_template('receiver_dashboard.html', requests=requests)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/request-blood', methods=['GET', 'POST'])
@login_required
def request_blood():
    if request.method == 'POST':
        try:
            blood_request = BloodRequest(
                requester_id=current_user.id,
                blood_type=request.form['blood_type'],
                units_needed=int(request.form['units']),
                urgency=request.form['urgency'],
                hospital=request.form['hospital'],
                notes=request.form.get('notes', ''),
                required_by=datetime.strptime(request.form['required_by'], '%Y-%m-%d') if request.form.get('required_by') else None
            )
            db.session.add(blood_request)
            db.session.commit()
            flash('Blood request created successfully!')
            return redirect(url_for('receiver_dashboard'))
        except Exception as e:
            logging.error(f"Blood request creation error: {str(e)}")
            flash('An error occurred while creating the request. Please try again.')
    return render_template('request_blood.html')

@app.route('/donate', methods=['GET', 'POST'])
@login_required
def donate():
    if current_user.role != 'donor':
        flash('Only donors can access this page.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            donation = Donation(
                donor_id=current_user.id,
                blood_type=current_user.blood_type,
                units=int(request.form['units']),
                center=request.form['center'],
                notes=request.form.get('notes', '')
            )
            db.session.add(donation)
            db.session.commit()
            flash('Donation recorded successfully!')
            return redirect(url_for('donor_dashboard'))
        except Exception as e:
            logging.error(f"Donation recording error: {str(e)}")
            flash('An error occurred while recording the donation. Please try again.')
    return render_template('donate.html')

def calculate_blood_compatibility(blood_type):
    #  This is a placeholder.  A proper implementation would depend on the blood type system used.
    #  For simplicity, we'll assume all types are compatible for this example.
    return ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']

@app.route('/blood-requests')
@login_required
def blood_requests():
    if current_user.role == 'admin':
        requests = BloodRequest.query.order_by(BloodRequest.created_at.desc()).all()
    elif current_user.role == 'receiver':
        requests = BloodRequest.query.filter_by(requester_id=current_user.id).order_by(BloodRequest.created_at.desc()).all()
    else:
        # For donors, show compatible requests based on their blood type
        compatible_types = calculate_blood_compatibility(current_user.blood_type)
        requests = BloodRequest.query.filter(BloodRequest.blood_type.in_(compatible_types)).order_by(BloodRequest.created_at.desc()).all()

    return render_template('blood_requests.html', requests=requests)


@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Here we'll just flash a message for now
        # In a real application, you'd want to send this to an email or save to database
        flash('Thank you for your message. We will get back to you soon!')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/teams')
def teams():
    return render_template('teams.html')

@app.route('/donation-tips')
def donation_tips():
    return render_template('donation_tips.html')

@app.route('/blood-banks')
def blood_banks():
    return render_template('blood_banks.html')

@app.route('/help-support')
def help_support():
    return render_template('help_support.html')

@app.route('/can-i-give-blood')
def eligibility_check():
    return render_template('eligibility_check.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Basic user information
            user = User(
                email=request.form['email'],
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                password_hash=generate_password_hash(request.form['password']),
                role=request.form.get('role', 'donor'),
                # Additional profile information
                blood_type=request.form.get('blood_type'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                gender=request.form.get('gender'),
                date_of_birth=datetime.strptime(request.form.get('date_of_birth', ''), '%Y-%m-%d') if request.form.get('date_of_birth') else None
            )

            if User.query.filter_by(email=user.email).first():
                flash('Email already registered')
                return render_template('register.html')

            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Registration successful!')
            return redirect(get_dashboard_route(user.role))
        except Exception as e:
            logging.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.')
            return render_template('register.html')
    return render_template('register.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)