from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models import db, User, Role, log_activity
from functools import wraps

auth = Blueprint('auth', __name__)

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
        
        user = User.query.filter_by(Username=username).first()
        
        if user is None or not user.verify_password(password):
            flash('Invalid username or password.')
            return render_template('login.html')
        
        if not user.IsActive:
            flash('Your account is disabled. Please contact an administrator.')
            return render_template('login.html')
        
        # Update last login time
        user.LastLogin = db.func.now()
        db.session.commit()
        
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
        
        # Check if username or email already exists
        if User.query.filter_by(Username=username).first():
            flash('Username already exists.')
            return render_template('register.html')
        
        if User.query.filter_by(Email=email).first():
            flash('Email already exists.')
            return render_template('register.html')
        
        # Create new user
        user = User(
            Username=username,
            Email=email,
            FirstName=first_name,
            LastName=last_name
        )
        user.password = password
        
        # Assign default role (Guest)
        guest_role = Role.query.filter_by(RoleName='Guest').first()
        if guest_role:
            user.roles.append(guest_role)
        
        db.session.add(user)
        db.session.commit()
        
        # Log the registration
        log_activity(
            user_id=user.UserID,
            action='INSERT',
            table_name='users',
            record_id=user.UserID,
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
        g.user = User.query.get(user_id)
        if g.user:
            g.roles = [role.RoleName for role in g.user.roles]
        else:
            g.roles = []
