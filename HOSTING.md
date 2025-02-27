# Hosting Instructions for Blood Donation System

## 1. Prerequisites

### System Requirements:
- Python 3.11 or higher
- PostgreSQL 13 or higher
- pip (Python package manager)

### Required Python Packages:
```bash
pip install flask flask-login flask-sqlalchemy psycopg2-binary werkzeug pyotp qrcode email-validator gunicorn
```

## 2. Database Setup

1. Install PostgreSQL:
   - For Windows: Download and install from https://www.postgresql.org/download/windows/
   - For macOS: `brew install postgresql`
   - For Ubuntu/Debian: `sudo apt install postgresql postgresql-contrib`

2. Start PostgreSQL Service:
   - Windows: It runs as a service automatically
   - macOS: `brew services start postgresql`
   - Linux: `sudo systemctl start postgresql`

3. Create Database:
```bash
# Login to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE blood_donation;
CREATE USER blood_admin WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE blood_donation TO blood_admin;

# Exit PostgreSQL
\q
```

## 3. Application Setup

1. Clone or download the application files to your local machine.

2. Create a `.env` file in the root directory with the following content:
```
DATABASE_URL=postgresql://blood_admin:your_secure_password@localhost:5432/blood_donation
SESSION_SECRET=your_secure_session_secret
```

3. Initialize the database:
```python
# Run Python in the project directory
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
```

## 4. Running the Application

### Development Mode:
```bash
python app.py
```
The application will be available at `http://localhost:5000`

### Production Mode (using Gunicorn):
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 5. Important Database Queries

Here are some useful database queries for managing the application:

1. List all users:
```sql
SELECT id, email, role, blood_type FROM "user";
```

2. Check blood requests:
```sql
SELECT br.id, u.email, br.blood_type, br.units_needed, br.status 
FROM blood_request br 
JOIN "user" u ON br.requester_id = u.id;
```

3. View donations:
```sql
SELECT d.id, u.email, d.blood_type, d.units, d.donation_date 
FROM donation d 
JOIN "user" u ON d.donor_id = u.id;
```

## 6. Security Considerations

1. Always use HTTPS in production
2. Keep SESSION_SECRET secure and unique
3. Regularly update dependencies
4. Back up your database regularly
5. Monitor application logs for suspicious activities

## 7. Maintenance

1. Database Backup:
```bash
pg_dump -U blood_admin blood_donation > backup.sql
```

2. Database Restore:
```bash
psql -U blood_admin blood_donation < backup.sql
```

3. Update Dependencies:
```bash
pip install --upgrade -r requirements.txt
```

## 8. Troubleshooting

1. Database Connection Issues:
   - Verify PostgreSQL is running
   - Check DATABASE_URL in .env file
   - Ensure database user has correct permissions

2. Application Errors:
   - Check application logs
   - Verify all required packages are installed
   - Ensure all environment variables are set correctly

3. 2FA Issues:
   - Check if pyotp is installed correctly
   - Verify user's TOTP secret is stored correctly
   - Ensure system time is synchronized

For additional support or questions, refer to the project documentation or contact the development team.
