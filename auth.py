from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models import User, Role, log_activity
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime
import pyodbc
import json

auth = Blueprint('auth', __name__)

# Database connection helper
def get_db_connection():
    from app import get_db_connection as app_db_conn
    return app_db_conn()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.')
            return redirect(url_for('auth.login', next=request.url))
        
        if not g.user or not any(role in g.roles for role in ['Admin']):
            flash('You do not have permission to access this page.')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE Username = ?", username)
            user_row = cursor.fetchone()
            
            if user_row is None or not check_password_hash(user_row.PasswordHash, password):
                flash('Invalid username or password.')
                return render_template('login.html')
            
            if not user_row.IsActive:
                flash('Your account is disabled. Please contact an administrator.')
                return render_template('login.html')
            
            # Create User object from row
            user = User.from_row(user_row)
            
            # Update last login time
            now = datetime.now()
            cursor.execute(
                "UPDATE users SET LastLogin = ? WHERE UserID = ?",
                now, user.UserID
            )
            
            # Load user roles
            cursor.execute(
                "SELECT r.* FROM roles r JOIN user_roles ur ON r.RoleID = ur.role_id WHERE ur.user_id = ?",
                user.UserID
            )
            roles = [Role.from_row(row) for row in cursor.fetchall()]
            user.roles = roles
            
            conn.commit()
            
            # Log the login activity
            log_activity(
                user_id=user.UserID,
                action='LOGIN',
                ip_address=request.remote_addr
            )
            
            # Store user in session
            session['user_id'] = user.UserID
            session.permanent = remember
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
                
            # Check user roles and redirect to appropriate dashboard
            user_roles = [role.RoleName for role in user.roles]
            
            if 'Admin' in user_roles:
                return redirect(url_for('dashboard'))
            elif 'Staff' in user_roles or 'Librarian' in user_roles:
                return redirect(url_for('staff_dashboard'))
            elif 'Member' in user_roles:
                return redirect(url_for('member_dashboard'))
            else:
                # Guest or other roles go to catalog
                return redirect(url_for('catalog'))
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE Username = ?", username)
            if cursor.fetchone()[0] > 0:
                flash('Username already exists.')
                return render_template('register.html')
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE Email = ?", email)
            if cursor.fetchone()[0] > 0:
                flash('Email already exists.')
                return render_template('register.html')
            
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            user.password = password  # This will hash the password
            
            # Insert into database
            cursor.execute(
                "INSERT INTO users (Username, PasswordHash, Email, FirstName, LastName, IsActive, CreatedAt, UpdatedAt) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                username, user.PasswordHash, email, first_name, last_name, 1, datetime.now(), datetime.now()
            )
            conn.commit()
            
            # Get the new user ID
            cursor.execute("SELECT UserID FROM users WHERE Username = ?", username)
            user_id = cursor.fetchone()[0]
            
            # Assign default role (Guest)
            cursor.execute("SELECT RoleID FROM roles WHERE RoleName = 'Guest'")
            guest_role_row = cursor.fetchone()
            
            if guest_role_row:
                cursor.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    user_id, guest_role_row[0]
                )
                conn.commit()
            
            # Log the registration
            log_activity(
                user_id=user_id,
                action='REGISTER',
                table_name='users',
                record_id=user_id,
                new_values={
                    'Username': username,
                    'Email': email,
                    'FirstName': first_name,
                    'LastName': last_name,
                },
                ip_address=request.remote_addr
            )
            
            flash('Registration successful! You can now login.')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth.route('/logout')
def logout():
    if 'user_id' in session:
        user_id = session['user_id']
        log_activity(
            user_id=user_id,
            action='LOGOUT',
            ip_address=request.remote_addr
        )
        
        session.pop('user_id', None)
        flash('You have been logged out.')
    
    return redirect(url_for('index'))

@auth.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        g.roles = []
    else:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get user data
                cursor.execute("SELECT * FROM users WHERE UserID = ?", user_id)
                user_row = cursor.fetchone()
                
                if user_row:
                    g.user = User.from_row(user_row)
                    
                    # Get user roles
                    cursor.execute(
                        "SELECT r.* FROM roles r "
                        "JOIN user_roles ur ON r.RoleID = ur.role_id "
                        "WHERE ur.user_id = ?",
                        user_id
                    )
                    
                    roles = [Role.from_row(row) for row in cursor.fetchall()]
                    g.user.roles = roles
                    g.roles = [role.RoleName for role in roles]
                else:
                    g.user = None
                    g.roles = []
        except Exception as e:
            print(f"Error loading user: {str(e)}")
            g.user = None
            g.roles = []
