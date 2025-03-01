# Create a new file: email_utils.py

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

def send_email(recipient, subject, body_html, body_text=None):
    """
    Send an email using the configured SMTP server
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject
        body_html: HTML content of the email
        body_text: Plain text version (optional)
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        # Email configuration - should be moved to environment variables
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_username = os.environ.get('SMTP_USERNAME', 'bloodbridge@example.com')
        smtp_password = os.environ.get('SMTP_PASSWORD', 'your-password')
        sender_email = os.environ.get('SENDER_EMAIL', 'bloodbridge@example.com')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'BloodBridge <{sender_email}>'
        msg['To'] = recipient
        
        # Attach text part if provided
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        
        # Attach HTML part
        msg.attach(MIMEText(body_html, 'html'))
        
        # Connect to server and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, recipient, msg.as_string())
        
        logger.info(f"Email sent to {recipient}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        return False

def send_password_reset_email(user, token, reset_url):
    """
    Send a password reset email to a user
    
    Args:
        user: User object
        token: Password reset token
        reset_url: Base URL for password reset (e.g., https://example.com/reset-password)
    
    Returns:
        bool: True if the email was sent successfully
    """
    reset_link = f"{reset_url}?token={token}"
    
    subject = "Reset Your BloodBridge Password"
    
    # HTML version
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #dc3545;">BloodBridge</h2>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h3>Hello {user.first_name},</h3>
                
                <p>We received a request to reset your password for your BloodBridge account.</p>
                
                <p>To reset your password, please click the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background-color: #dc3545; color: white; padding: 12px 25px; text-decoration: none; border-radius: 4px; font-weight: bold;">Reset Password</a>
                </div>
                
                <p>If you didn't request this password reset, you can ignore this email and your password will remain unchanged.</p>
                
                <p>This password reset link will expire in 24 hours.</p>
                
                <p>Thank you,<br>
                The BloodBridge Team</p>
            </div>
            
            <div style="margin-top: 20px; font-size: 12px; color: #6c757d; text-align: center;">
                <p>If you're having trouble clicking the button, copy and paste the URL below into your web browser:</p>
                <p style="word-break: break-all;">{reset_link}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_content = f"""
    Hello {user.first_name},
    
    We received a request to reset your password for your BloodBridge account.
    
    To reset your password, please visit the link below:
    
    {reset_link}
    
    If you didn't request this password reset, you can ignore this email and your password will remain unchanged.
    
    This password reset link will expire in 24 hours.
    
    Thank you,
    The BloodBridge Team
    """
    
    return send_email(user.email, subject, html_content, text_content)