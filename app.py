import os
import json
import logging
import re
from datetime import datetime, timedelta
from flask import Flask, abort, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import qrcode
import io
import base64

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app first
app = Flask(__name__)

# Then configure the app
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_123")
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:Ss%40071424@localhost:5432/bloodbridge"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# File upload configuration
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'id_documents'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'medical_certificates'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'address_proofs'), exist_ok=True)

# Import these after initializing app
from extensions import db
from models import PasswordReset, User, BloodRequest, Donation, DonorVerification
from utils import admin_required, calculate_blood_compatibility, donor_required, receiver_required, format_verification_status, calculate_next_donation_date

# Initialize SQLAlchemy
db.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_file(file, subfolder):
    """Save file to upload folder and return filename"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to filename to make it unique
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
        file.save(upload_path)
        return filename
    return None

# Context processor for common variables
@app.context_processor
def inject_common_variables():
    context = {'now': datetime.utcnow()}
    
    # If user is logged in as admin, inject admin dashboard data
    if current_user.is_authenticated and current_user.role == 'admin':
        # Get counts for admin dashboard
        context['pending_verifications_count'] = DonorVerification.query.filter_by(status='pending').count()
        context['pending_requests_count'] = BloodRequest.query.filter_by(status='pending').count()
        context['pending_donations_count'] = Donation.query.filter_by(status='pending').count()
        
        # Get recent verifications for admin dashboard
        context['recent_verifications'] = DonorVerification.query.order_by(
            DonorVerification.submission_date.desc()
        ).limit(5).all()
    
    # Add format_verification_status function to templates
    context['format_verification_status'] = format_verification_status
    
    return context

# Routes
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
        flash('Invalid email or password', 'danger')
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
        flash('Invalid 2FA code', 'danger')

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
            flash('Two-factor authentication has been enabled', 'success')
            return redirect(url_for('profile'))
        flash('Invalid 2FA code', 'danger')

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
    flash('Two-factor authentication has been disabled', 'success')
    return redirect(url_for('profile'))

@app.route('/verify-donor', methods=['GET', 'POST'])
@login_required
@donor_required
def verify_donor():
    """Page for donors to submit verification documents"""
    # Check if user already has a pending or approved verification
    existing_verification = DonorVerification.query.filter(
        DonorVerification.donor_id == current_user.id, 
        DonorVerification.status.in_(['pending', 'approved'])
    ).first()
    
    if existing_verification and existing_verification.status == 'approved':
        flash('You are already verified!', 'info')
        return redirect(url_for('donor_dashboard'))
    
    if existing_verification and existing_verification.status == 'pending':
        flash('Your verification is still being reviewed.', 'info')
        return redirect(url_for('verification_status'))
    
    if request.method == 'POST':
        try:
            # Handle file uploads
            id_document = request.files.get('id_document')
            medical_certificate = request.files.get('medical_certificate')
            address_proof = request.files.get('address_proof')
            
            id_filename = save_file(id_document, 'id_documents') if id_document else None
            medical_filename = save_file(medical_certificate, 'medical_certificates') if medical_certificate else None
            address_filename = save_file(address_proof, 'address_proofs') if address_proof else None
            
            # Capture questionnaire responses
            questionnaire_data = {
                'recent_illness': request.form.get('recent_illness'),
                'medication': request.form.get('medication'),
                'last_donation': request.form.get('last_donation'),
                'has_allergies': request.form.get('has_allergies'),
                'allergies_details': request.form.get('allergies_details'),
                'blood_transfusion': request.form.get('blood_transfusion'),
                'recent_surgery': request.form.get('recent_surgery'),
                'chronic_conditions': request.form.get('chronic_conditions'),
                'travel_history': request.form.get('travel_history'),
                'consented': request.form.get('consent') == 'on'
            }
            
            # Create verification record
            verification = DonorVerification(
                donor_id=current_user.id,
                status='pending',
                id_document_filename=id_filename,
                medical_certificate_filename=medical_filename,
                address_proof_filename=address_filename,
                questionnaire_responses=json.dumps(questionnaire_data)
            )
            
            # Update user verification status
            current_user.verification_status = 'pending'
            
            db.session.add(verification)
            db.session.commit()
            
            flash('Your verification documents have been submitted and will be reviewed shortly.', 'success')
            return redirect(url_for('verification_status'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Verification submission error: {str(e)}")
            flash('An error occurred while submitting your verification. Please try again.', 'danger')
    
    return render_template('verify_donor.html')

@app.route('/verification-status')
@login_required
@donor_required
def verification_status():
    """Page for donors to check their verification status"""
    verification = DonorVerification.query.filter_by(donor_id=current_user.id).order_by(DonorVerification.submission_date.desc()).first()
    
    if not verification:
        flash('You have not submitted any verification documents yet.', 'info')
        return redirect(url_for('verify_donor'))
    
    return render_template('verification_status.html', verification=verification)

@app.route('/admin/verifications')
@login_required
@admin_required
def admin_verifications():
    """Admin page to view all pending verifications"""
    status_filter = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    if status_filter == 'all':
        verifications = DonorVerification.query.order_by(DonorVerification.submission_date.desc())
    else:
        verifications = DonorVerification.query.filter_by(status=status_filter).order_by(DonorVerification.submission_date.desc())
    
    pagination = verifications.paginate(page=page, per_page=per_page)
    
    return render_template('admin_verifications.html', pagination=pagination, status_filter=status_filter)

@app.route('/admin/review-verification/<int:verification_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def review_verification(verification_id):
    """Admin page to review a specific verification"""
    verification = DonorVerification.query.get_or_404(verification_id)
    donor = User.query.get(verification.donor_id)
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            notes = request.form.get('notes')
            
            if action not in ['approve', 'reject']:
                flash('Invalid action.', 'danger')
                return redirect(url_for('review_verification', verification_id=verification_id))
            
            verification.status = 'approved' if action == 'approve' else 'rejected'
            verification.reviewer_id = current_user.id
            verification.review_date = datetime.utcnow()
            verification.review_notes = notes
            
            # Update user verification status
            donor.verification_status = verification.status
            if action == 'approve':
                donor.is_verified = True
                donor.verification_date = datetime.utcnow()
            else:
                donor.is_verified = False
            
            db.session.commit()
            
            flash(f'Verification has been {verification.status}.', 'success')
            return redirect(url_for('admin_verifications'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Verification review error: {str(e)}")
            flash('An error occurred while reviewing the verification. Please try again.', 'danger')
    
    # Parse questionnaire responses
    questionnaire = json.loads(verification.questionnaire_responses) if verification.questionnaire_responses else {}
    
    return render_template('review_verification.html', verification=verification, donor=donor, questionnaire=questionnaire)

@app.route('/view-document/<document_type>/<filename>')
@login_required
def view_document(document_type, filename):
    """Route to view uploaded documents"""
    # Security check: make sure only admins or the document owner can view documents
    if document_type not in ['id_documents', 'medical_certificates', 'address_proofs']:
        abort(404)
    
    # Find which verification this document belongs to
    verification = None
    if document_type == 'id_documents':
        verification = DonorVerification.query.filter_by(id_document_filename=filename).first()
    elif document_type == 'medical_certificates':
        verification = DonorVerification.query.filter_by(medical_certificate_filename=filename).first()
    elif document_type == 'address_proofs':
        verification = DonorVerification.query.filter_by(address_proof_filename=filename).first()
    
    if not verification:
        abort(404)
    
    # Check if current user is authorized to view this document
    if current_user.role != 'admin' and verification.donor_id != current_user.id:
        abort(403)
    
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], document_type), filename)

@app.route('/donate', methods=['GET', 'POST'])
@login_required
def donate():
    if current_user.role != 'donor':
        flash('Only donors can access this page.', 'warning')
        return redirect(url_for('index'))
    
    # Check if donor is verified
    if not current_user.is_verified:
        flash('You need to be verified before you can donate blood. Please complete the verification process.', 'warning')
        return redirect(url_for('verify_donor'))
    
    # Check eligibility based on last donation date
    can_donate, message = current_user.can_donate()
    if not can_donate:
        flash(message, 'warning')
        return redirect(url_for('donor_dashboard'))

    if request.method == 'POST':
        try:
            donation = Donation(
                donor_id=current_user.id,
                blood_type=current_user.blood_type,
                units=int(request.form['units']),
                center=request.form['center'],
                notes=request.form.get('notes', ''),
                status='pending'  # Start with pending status
            )
            db.session.add(donation)
            
            # Update user's donation dates
            current_user.last_donation_date = datetime.utcnow()
            current_user.next_eligible_date = calculate_next_donation_date(current_user.last_donation_date)
            
            db.session.commit()
            flash('Donation recorded successfully! It will be verified by the blood bank.', 'success')
            return redirect(url_for('donor_dashboard'))
        except Exception as e:
            logging.error(f"Donation recording error: {str(e)}")
            flash('An error occurred while recording the donation. Please try again.', 'danger')
    return render_template('donate.html')

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
    
    # Get recent verifications
    recent_verifications = DonorVerification.query.order_by(
        DonorVerification.submission_date.desc()
    ).limit(5).all()
    
    return render_template(
        'admin_dashboard.html',
        blood_requests=blood_requests,
        donations=donations,
        recent_verifications=recent_verifications
    )

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
            flash('Blood request created successfully!', 'success')
            return redirect(url_for('receiver_dashboard'))
        except Exception as e:
            logging.error(f"Blood request creation error: {str(e)}")
            flash('An error occurred while creating the request. Please try again.', 'danger')
    return render_template('request_blood.html')

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
        flash('Thank you for your message. We will get back to you soon!', 'success')
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
                flash('Email already registered', 'danger')
                return render_template('register.html')

            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Registration successful!', 'success')
            return redirect(get_dashboard_route(user.role))
        except Exception as e:
            logging.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('register.html')
    return render_template('register.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
from email_utils import send_password_reset_email

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('forgot_password'))
        
        user = User.query.filter_by(email=email).first()
        
        # Even if the user doesn't exist, don't reveal this information
        # to prevent email enumeration attacks
        if user:
            token = user.generate_password_reset_token()
            
            # In production, use the actual host
            reset_url = request.host_url.rstrip('/') + url_for('reset_password')
            
            if send_password_reset_email(user, token, reset_url):
                flash('Password reset instructions have been sent to your email.', 'success')
            else:
                flash('There was an error sending the password reset email. Please try again later.', 'danger')
        else:
            # Log this but don't tell the user (to prevent email enumeration)
            logging.info(f"Password reset requested for non-existent email: {email}")
            # Still show success message to prevent email enumeration
            flash('If your email is registered, you will receive password reset instructions.', 'success')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset with token verification"""
    token = request.args.get('token') or request.form.get('token')
    
    if not token:
        flash('Invalid or missing reset token.', 'danger')
        return redirect(url_for('login'))
    
    # Find the reset token in the database
    reset = PasswordReset.query.filter_by(token=token, used=False).first()
    
    if not reset or not reset.is_valid():
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.get(reset.user_id)
    
    if not user:
        flash('User account not found.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)
        
        # Update the user's password
        user.password_hash = generate_password_hash(password)
        
        # Invalidate the token
        reset.invalidate()
        
        db.session.commit()
        
        flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

# Admin route for resetting user passwords
@app.route('/admin/reset-user-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    """Allow admins to reset user passwords"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        password = request.form.get('password')
        
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('admin_reset_password.html', user=user)
        
        # Update the user's password
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        
        flash(f'Password for {user.email} has been reset successfully.', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_reset_password.html', user=user)

# Route to view all users (for admin)
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Admin page to view and manage users"""
    role_filter = request.args.get('role', 'all')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    query = User.query
    
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    if search_query:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search_query}%'),
                User.first_name.ilike(f'%{search_query}%'),
                User.last_name.ilike(f'%{search_query}%')
            )
        )
    
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin_users.html', 
                          pagination=pagination, 
                          role_filter=role_filter,
                          search_query=search_query)
# Route for admin dashboard
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Get counts for admin dashboard
    pending_verifications_count = DonorVerification.query.filter_by(status='pending').count()
    pending_requests_count = BloodRequest.query.filter_by(status='pending').count()
    pending_donations_count = Donation.query.filter_by(status='pending').count()
    
    # Get recent data for dashboard
    blood_requests = BloodRequest.query.order_by(BloodRequest.created_at.desc()).limit(5).all()
    donations = Donation.query.order_by(Donation.donation_date.desc()).limit(5).all()
    
    # Get recent verifications
    recent_verifications = DonorVerification.query.order_by(
        DonorVerification.submission_date.desc()
    ).limit(5).all()
    
    # Get admin action logs
    recent_admin_logs = AdminActionLog.query.order_by(
        AdminActionLog.timestamp.desc()
    ).limit(10).all()
    
    return render_template(
        'admin_dashboard.html',
        pending_verifications_count=pending_verifications_count,
        pending_requests_count=pending_requests_count,
        pending_donations_count=pending_donations_count,
        blood_requests=blood_requests,
        donations=donations,
        recent_verifications=recent_verifications,
        recent_admin_logs=recent_admin_logs
    )

# Route for admin users page
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Admin page to view and manage users"""
    role_filter = request.args.get('role', 'all')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    query = User.query
    
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    if search_query:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search_query}%'),
                User.first_name.ilike(f'%{search_query}%'),
                User.last_name.ilike(f'%{search_query}%')
            )
        )
    
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin_users.html', 
                          pagination=pagination, 
                          role_filter=role_filter,
                          search_query=search_query)

# Route for admin reset user password
@app.route('/admin/reset-user-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    """Allow admins to reset user passwords"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_reset = request.form.get('confirm_reset')
        
        # Validate confirmation
        if not confirm_reset:
            flash('You must confirm the password reset.', 'danger')
            return render_template('admin_reset_password.html', user=user)
        
        # Validate password complexity
        is_valid, error_message = validate_password_complexity(password)
        if not is_valid:
            flash(error_message, 'danger')
            return render_template('admin_reset_password.html', user=user)
        
        try:
            # Update the user's password
            old_hash = user.password_hash  # Keep for logging
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            
            # Log the password reset action
            log_admin_action(
                admin_user=current_user, 
                action_type='password_reset', 
                target_user=user,
                details={
                    'method': 'admin_reset',
                    'old_hash_changed': old_hash != user.password_hash
                }
            )
            
            flash(f'Password for {user.email} has been reset successfully.', 'success')
            return redirect(url_for('admin_users'))
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error resetting password for user {user.email}: {str(e)}")
            flash('An error occurred while resetting the password.', 'danger')
    
    return render_template('admin_reset_password.html', user=user)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)