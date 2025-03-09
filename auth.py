import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

auth = Blueprint('auth', __name__, template_folder='templates')

def get_db_connection():
    import pyodbc  # Import here to avoid circular imports
    return pyodbc.connect(Config.DB_CONNECTION_STRING)

# Add this function to check if user has a specific role
def user_has_role(user_id, role_name):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM user_roles ur "
            "JOIN roles r ON ur.role_id = r.RoleID "
            "WHERE ur.user_id = ? AND r.RoleName = ?",
            user_id, role_name
        )
        return cursor.fetchone()[0] > 0

# Update login_required to check current user ID
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.path))
            
        return view(**kwargs)
    return wrapped_view

# Add staff_required decorator for staff-only functions
def staff_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        
        if not (user_has_role(g.user['UserID'], 'Admin') or user_has_role(g.user['UserID'], 'Staff')):
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('dashboard'))
            
        return view(**kwargs)
    return wrapped_view

# Update admin_required to use the user_has_role function
def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.path))
            
        if not user_has_role(g.user['UserID'], 'Admin'):
            flash('Administrator access required', 'danger')
            return redirect(url_for('dashboard'))
            
        return view(**kwargs)
    return wrapped_view

# Load logged-in user before each request
@auth.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    
    if user_id is None:
        g.user = None
    else:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE UserID = ?", user_id)
            user = cursor.fetchone()
            
            # Convert pyodbc.Row to dictionary
            if user:
                user_dict = {column[0]: value for column, value in zip(cursor.description, user)}
                
                # Add user roles
                cursor.execute(
                    "SELECT r.RoleName FROM user_roles ur "
                    "JOIN roles r ON ur.role_id = r.RoleID "
                    "WHERE ur.user_id = ?", 
                    user_dict['UserID']
                )
                roles = [row[0] for row in cursor.fetchall()]
                user_dict['roles'] = roles
                user_dict['is_admin'] = 'Admin' in roles
                user_dict['is_staff'] = 'Staff' in roles or 'Admin' in roles
                
                g.user = user_dict

@auth.route('/login', methods=('GET', 'POST'))
def login():
    next_url = request.args.get('next', '')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        error = None
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE Username = ?", username)
            user = cursor.fetchone()
            
        if user is None:
            error = 'Incorrect username or password.'
            print(f"Login failed: User '{username}' not found.")
        elif not check_password_hash(user.PasswordHash, password):
            error = 'Incorrect username or password.'
            print(f"Login failed: Incorrect password for user '{username}'.")
        elif not user.IsActive:
            error = 'This account has been disabled.'
            print(f"Login failed: User '{username}' is disabled.")
            
        if error is None:
            # Store user ID in session
            session.clear()
            session['user_id'] = user.UserID
            print(f"Login successful: User '{username}' logged in.")
            
            # Get redirect URL from form or use default
            redirect_url = request.form.get('next') or url_for('dashboard')
            return redirect(redirect_url)
            
        flash(error)
    
    return render_template('auth/login.html', next=next_url)

@auth.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@auth.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        
        error = None
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT UserID FROM users WHERE Username = ?", (username,))
            if cursor.fetchone() is not None:
                error = f"User {username} is already registered."
            
            # Check if email already exists
            cursor.execute("SELECT UserID FROM users WHERE Email = ?", (email,))
            if cursor.fetchone() is not None:
                error = f"Email {email} is already registered."
                
            if error is None:
                # Hash the password and insert user
                password_hash = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO users (Username, PasswordHash, Email, FirstName, LastName, IsActive) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (username, password_hash, email, first_name, last_name, 1)
                )
                conn.commit()
                
                # Get the user ID
                cursor.execute("SELECT UserID FROM users WHERE Username = ?", (username,))
                user_id = cursor.fetchone()[0]
                
                # Assign Member role by default
                cursor.execute("SELECT RoleID FROM roles WHERE RoleName = 'Member'")
                role_id = cursor.fetchone()[0]
                
                cursor.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    (user_id, role_id)
                )
                conn.commit()
                
                flash('Registration successful! Please log in.')
                return redirect(url_for('auth.login'))
        
        flash(error)
    
    return render_template('auth/register.html')
