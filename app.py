import os
import shutil
import pyodbc
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from auth import auth, login_required, admin_required

app = Flask(__name__)

# Configure app with Config class
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
app.config['BACKUP_FOLDER'] = Config.BACKUP_FOLDER

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')

# Initialize app with Config class
Config.init_app(app)

# Create database connection
def get_db_connection():
    return pyodbc.connect(Config.DB_CONNECTION_STRING)

# Replace before_first_request with a function that runs at startup
def initialize_database():
    with app.app_context():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if tables exist and create them if they don't
            # This would typically be done with SQL scripts rather than here
            # But for simplicity, we'll check for a critical table
            
            cursor.execute("IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users') BEGIN "
                        "EXEC('CREATE DATABASE library_system') END")
            
            # Create default roles if they don't exist
            create_default_roles()
            # Create admin user if no users exist
            create_admin_user()
            # Create default book categories
            create_default_categories()

def create_default_roles():
    default_roles = ['Admin', 'Staff', 'Member', 'Guest']
    descriptions = {
        'Admin': 'Full access to all system features',
        'Staff': 'Can manage books, members, and loans',
        'Member': 'Regular library member',
        'Guest': 'Limited access'
    }
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for role_name in default_roles:
            # Check if role exists
            cursor.execute("SELECT COUNT(*) FROM roles WHERE RoleName = ?", role_name)
            if cursor.fetchone()[0] == 0:
                # Role doesn't exist, create it
                cursor.execute(
                    "INSERT INTO roles (RoleName, Description) VALUES (?, ?)",
                    role_name, descriptions.get(role_name)
                )
        
        conn.commit()

def create_admin_user():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if any users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Create admin user
            password_hash = generate_password_hash('admin')
            cursor.execute(
                "INSERT INTO users (Username, PasswordHash, Email, FirstName, LastName, IsActive) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                'admin', password_hash, 'admin@library.com', 'Admin', 'User', 1
            )
            
            # Get the user ID of the inserted admin
            cursor.execute("SELECT UserID FROM users WHERE Username = 'admin'")
            admin_user_id = cursor.fetchone()[0]
            
            # Assign admin role
            cursor.execute("SELECT RoleID FROM roles WHERE RoleName = 'Admin'")
            admin_role_id = cursor.fetchone()[0]
            
            if admin_role_id:
                cursor.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    admin_user_id, admin_role_id
                )
            
            conn.commit()
            print("Created default admin user: username='admin', password='admin'")

def create_default_categories():
    default_categories = [
        'Fiction', 'Non-Fiction', 'Science Fiction', 'Mystery', 
        'Biography', 'History', 'Children', 'Science', 'Technology',
        'Arts', 'Philosophy', 'Religion', 'Business', 'Travel'
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if categories exist
        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]
        
        if category_count == 0:
            for category_name in default_categories:
                cursor.execute(
                    "INSERT INTO categories (CategoryName) VALUES (?)",
                    category_name
                )
            
            conn.commit()
            print("Created default book categories")

# Helper function for activity logging
def log_activity(user_id, action, table_name=None, record_id=None, old_values=None, new_values=None, ip_address=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Convert dictionaries to JSON strings if they exist
        old_values_json = json.dumps(old_values) if old_values else None
        new_values_json = json.dumps(new_values) if new_values else None
        
        cursor.execute(
            "INSERT INTO activity_logs (UserID, Action, TableName, RecordID, OldValues, NewValues, IPAddress) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            user_id, action, table_name, record_id, old_values_json, new_values_json, ip_address
        )
        
        conn.commit()

# Index route
@app.route('/')
def index():
    # Get some featured books for the homepage using MS SQL's NEWID() for random ordering
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 6 b.*, c.CategoryName FROM books b "
            "LEFT JOIN categories c ON b.CategoryID = c.CategoryID "
            "ORDER BY NEWID()"
        )
        
        # Convert to list of dictionaries
        columns = [column[0] for column in cursor.description]
        featured_books = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    now = datetime.now()
    return render_template('index.html', featured_books=featured_books, now=now)

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get statistics for dashboard
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM members")
        member_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM loans WHERE Status = 'Borrowed'")
        active_loans = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM loans WHERE DueDate < GETDATE() AND Status = 'Borrowed'")
        overdue_loans = cursor.fetchone()[0]
        
        # Recent activities
        cursor.execute(
            "SELECT TOP 10 a.*, u.Username "
            "FROM activity_logs a "
            "LEFT JOIN users u ON a.UserID = u.UserID "
            "ORDER BY a.ChangedAt DESC"
        )
        columns = [column[0] for column in cursor.description]
        recent_activities = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Recent loans
        cursor.execute(
            "SELECT TOP 5 l.*, b.Title as BookTitle, m.FirstName + ' ' + m.LastName as MemberName "
            "FROM loans l "
            "JOIN books b ON l.BookID = b.BookID "
            "JOIN members m ON l.MemberID = m.MemberID "
            "ORDER BY l.LoanDate DESC"
        )
        columns = [column[0] for column in cursor.description]
        recent_loans = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return render_template(
        'dashboard.html',
        book_count=book_count,
        member_count=member_count,
        active_loans=active_loans,
        overdue_loans=overdue_loans,
        recent_activities=recent_activities,
        recent_loans=recent_loans
    )

# Staff Dashboard
@app.route('/staff_dashboard')
@login_required
def staff_dashboard():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Staff-specific stats and functionality
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM loans WHERE Status = 'Borrowed'")
        active_loans = cursor.fetchone()[0]
        
        # More staff-relevant stats
    
    return render_template(
        'staff_dashboard.html',
        book_count=book_count,
        active_loans=active_loans,
        # Additional staff-specific data
    )

# Member Dashboard
@app.route('/member_dashboard')
@login_required
def member_dashboard():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get the member associated with the logged-in user
        cursor.execute("SELECT * FROM members WHERE UserID = ?", g.user.UserID)
        member = cursor.fetchone()
        
        if member:
            # Get member's active loans
            cursor.execute(
                "SELECT * FROM loans WHERE MemberID = ? AND Status IN ('Borrowed', 'Overdue')",
                member.MemberID
            )
            active_loans = cursor.fetchall()
            
            # Get loan history
            cursor.execute(
                "SELECT TOP 5 * FROM loans WHERE MemberID = ? AND Status = 'Returned' ORDER BY ReturnDate DESC",
                member.MemberID
            )
            loan_history = cursor.fetchall()
            
            return render_template(
                'member_dashboard.html',
                member=member,
                active_loans=active_loans,
                loan_history=loan_history
            )
        else:
            flash('No member profile found for your account.')
            return redirect(url_for('catalog'))

# Book catalog route
@app.route('/catalog')
def catalog():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
    
    return render_template('catalog.html', books=books, categories=categories)

# Single book view
@app.route('/book/<int:book_id>')
def view_book(book_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM books WHERE BookID = ?", book_id)
        book = cursor.fetchone()
    
    return render_template('book_details.html', book=book)

# Member listing
@app.route('/members')
@login_required
def list_members():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM members")
        members = cursor.fetchall()
    
    return render_template('members.html', members=members)

# Loan listing
@app.route('/loans')
@login_required
def list_loans():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM loans")
        loans = cursor.fetchall()
    
    return render_template('loans.html', loans=loans)

# User management
@app.route('/admin/users')
@admin_required
def admin_users():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
    
    return render_template('users.html', users=users)

# Add user
@app.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        roles = request.form.getlist('roles')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE Username = ?", username)
            if cursor.fetchone()[0] > 0:
                flash('Username already exists.')
                return redirect(url_for('admin_users'))
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE Email = ?", email)
            if cursor.fetchone()[0] > 0:
                flash('Email already exists.')
                return redirect(url_for('admin_users'))
            
            # Create new user
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (Username, PasswordHash, Email, FirstName, LastName, IsActive) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                username, password_hash, email, first_name, last_name, 1
            )
            
            # Get the user ID of the inserted user
            cursor.execute("SELECT UserID FROM users WHERE Username = ?", username)
            user_id = cursor.fetchone()[0]
            
            # Assign roles
            for role_name in roles:
                cursor.execute("SELECT RoleID FROM roles WHERE RoleName = ?", role_name)
                role_id = cursor.fetchone()[0]
                if role_id:
                    cursor.execute(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                        user_id, role_id
                    )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='INSERT',
                table_name='users',
                record_id=user_id,
                new_values={
                    'Username': username,
                    'Email': email,
                    'FirstName': first_name,
                    'LastName': last_name,
                    'Roles': roles
                },
                ip_address=request.remote_addr
            )
            
            flash(f'User {username} has been created.')
            return redirect(url_for('admin_users'))

# Edit user
@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
@admin_required
def admin_edit_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE UserID = ?", user_id)
        user = cursor.fetchone()
        
        if request.method == 'POST':
            # Store old values for logging
            old_values = {
                'Email': user.Email,
                'FirstName': user.FirstName,
                'LastName': user.LastName,
                'Roles': user.Roles
            }
            
            email = request.form.get('email')
            first_name = request.form.get('firstName')
            last_name = request.form.get('lastName')
            
            # Update user details
            cursor.execute(
                "UPDATE users SET Email = ?, FirstName = ?, LastName = ? WHERE UserID = ?",
                email, first_name, last_name, user_id
            )
            
            # Update roles
            cursor.execute("DELETE FROM user_roles WHERE user_id = ?", user_id)
            role_names = request.form.getlist('roles')
            for role_name in role_names:
                cursor.execute("SELECT RoleID FROM roles WHERE RoleName = ?", role_name)
                role_id = cursor.fetchone()[0]
                if role_id:
                    cursor.execute(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                        user_id, role_id
                    )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='UPDATE',
                table_name='users',
                record_id=user_id,
                old_values=old_values,
                new_values={
                    'Email': email,
                    'FirstName': first_name,
                    'LastName': last_name,
                    'Roles': ', '.join(role_names)
                },
                ip_address=request.remote_addr
            )
            
            flash(f'User {user.Username} has been updated.')
        
        return redirect(url_for('admin_users'))

# Reset password
@app.route('/admin/users/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE UserID = ?", user_id)
        user = cursor.fetchone()
        
        if request.method == 'POST':
            new_password = request.form.get('newPassword')
            confirm_password = request.form.get('confirmPassword')
            
            if new_password != confirm_password:
                flash('Passwords do not match.')
                return redirect(url_for('admin_users'))
            
            password_hash = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET PasswordHash = ? WHERE UserID = ?",
                password_hash, user_id
            )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='UPDATE',
                table_name='users',
                record_id=user_id,
                old_values={'PasswordHash': '***'},
                new_values={'PasswordHash': '***'},
                ip_address=request.remote_addr
            )
            
            flash(f'Password for {user.Username} has been reset.')
        
        return redirect(url_for('admin_users'))

# Toggle user status
@app.route('/admin/users/toggle-status/<int:user_id>', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE UserID = ?", user_id)
        user = cursor.fetchone()
        
        if request.method == 'POST':
            old_status = user.IsActive
            new_status = not old_status
            cursor.execute(
                "UPDATE users SET IsActive = ? WHERE UserID = ?",
                new_status, user_id
            )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='UPDATE',
                table_name='users',
                record_id=user_id,
                old_values={'IsActive': old_status},
                new_values={'IsActive': new_status},
                ip_address=request.remote_addr
            )
            
            status_text = 'enabled' if new_status else 'disabled'
            flash(f'User {user.Username} has been {status_text}.')
        
        return redirect(url_for('admin_users'))

# Role management
@app.route('/admin/roles')
@admin_required
def admin_roles():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM roles")
        roles = cursor.fetchall()
    
    return render_template('roles.html', roles=roles)

# Add role
@app.route('/admin/roles/add', methods=['POST'])
@admin_required
def admin_add_role():
    if request.method == 'POST':
        role_name = request.form.get('roleName')
        description = request.form.get('description')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if role already exists
            cursor.execute("SELECT COUNT(*) FROM roles WHERE RoleName = ?", role_name)
            if cursor.fetchone()[0] > 0:
                flash('Role already exists.')
                return redirect(url_for('admin_roles'))
            
            # Create new role
            cursor.execute(
                "INSERT INTO roles (RoleName, Description) VALUES (?, ?)",
                role_name, description
            )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='INSERT',
                table_name='roles',
                record_id=cursor.lastrowid,
                new_values={
                    'RoleName': role_name,
                    'Description': description
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Role {role_name} has been created.')
        
        return redirect(url_for('admin_roles'))

# Edit role
@app.route('/admin/roles/edit/<int:role_id>', methods=['POST'])
@admin_required
def admin_edit_role(role_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM roles WHERE RoleID = ?", role_id)
        role = cursor.fetchone()
        
        if request.method == 'POST':
            # Store old values for logging
            old_values = {
                'RoleName': role.RoleName,
                'Description': role.Description
            }
            
            role_name = request.form.get('roleName')
            description = request.form.get('description')
            
            # Check if role is a system role
            system_roles = ['Admin', 'Staff', 'Member', 'Guest']
            if role.RoleName in system_roles:
                # Only update description for system roles
                cursor.execute(
                    "UPDATE roles SET Description = ? WHERE RoleID = ?",
                    description, role_id
                )
            else:
                cursor.execute(
                    "UPDATE roles SET RoleName = ?, Description = ? WHERE RoleID = ?",
                    role_name, description, role_id
                )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='UPDATE',
                table_name='roles',
                record_id=role_id,
                old_values=old_values,
                new_values={
                    'RoleName': role_name,
                    'Description': description
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Role {role_name} has been updated.')
        
        return redirect(url_for('admin_roles'))

# Delete role
@app.route('/admin/roles/delete/<int:role_id>', methods=['POST'])
@admin_required
def admin_delete_role(role_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM roles WHERE RoleID = ?", role_id)
        role = cursor.fetchone()
        
        # Prevent deletion of system roles
        system_roles = ['Admin', 'Staff', 'Member', 'Guest']
        if role.RoleName in system_roles:
            flash('Cannot delete system roles.')
            return redirect(url_for('admin_roles'))
        
        # Store role info for logging
        role_info = {
            'RoleID': role.RoleID,
            'RoleName': role.RoleName,
            'Description': role.Description
        }
        
        # Delete role
        cursor.execute("DELETE FROM roles WHERE RoleID = ?", role_id)
        conn.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='DELETE',
            table_name='roles',
            record_id=role_id,
            old_values=role_info,
            ip_address=request.remote_addr
        )
        
        flash(f'Role {role.RoleName} has been deleted.')
        return redirect(url_for('admin_roles'))

# Activity logs
@app.route('/admin/logs')
@admin_required
def admin_logs():
    action = request.args.get('action')
    table = request.args.get('table')
    user_id = request.args.get('user_id')
    days = request.args.get('days')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Base query
        query = "SELECT * FROM activity_logs WHERE 1=1"
        params = []
        
        if action:
            query += " AND Action = ?"
            params.append(action)
        
        if table:
            query += " AND TableName = ?"
            params.append(table)
        
        if user_id:
            query += " AND UserID = ?"
            params.append(user_id)
        
        if days:
            days_ago = datetime.now() - timedelta(days=int(days))
            query += " AND ChangedAt >= ?"
            params.append(days_ago)
        
        query += " ORDER BY ChangedAt DESC"
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # Get unique actions and tables for filters
        cursor.execute("SELECT DISTINCT Action FROM activity_logs")
        actions = cursor.fetchall()
        
        cursor.execute("SELECT DISTINCT TableName FROM activity_logs")
        tables = cursor.fetchall()
        
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
    
    return render_template(
        'logs.html',
        logs=logs,
        actions=actions,
        tables=tables,
        users=users,
        selected_action=action,
        selected_table=table,
        selected_user_id=user_id,
        selected_days=int(days) if days else None
    )

# Backup and recovery
@app.route('/admin/backup', methods=['GET', 'POST'])
@admin_required
def admin_backup():
    message = None
    status = None
    
    if request.method == 'POST':
        backup_type = request.form.get('backup_type', 'FULL')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{backup_type}_backup_{timestamp}.bak"
        backup_path = os.path.join(app.config['BACKUP_FOLDER'], backup_filename)
        
        try:
            # Execute backup using SQL Server's BACKUP DATABASE command
            # Note: This would typically use direct SQL execution or a stored procedure
            
            # For demonstration, we'll create a dummy backup file
            with open(backup_path, 'w') as f:
                f.write(f"Simulated {backup_type} backup created at {datetime.now()}")
            
            # Log the backup activity
            log_activity(
                user_id=g.user.UserID,
                action='BACKUP',
                table_name='DATABASE',
                new_values={'BackupType': backup_type, 'FileName': backup_filename},
                ip_address=request.remote_addr
            )
            
            message = f"Database backup '{backup_filename}' created successfully."
            status = 'success'
        except Exception as e:
            message = f"Error creating backup: {str(e)}"
            status = 'error'
    
    # Get existing backups
    backups = []
    if os.path.exists(app.config['BACKUP_FOLDER']):
        for filename in os.listdir(app.config['BACKUP_FOLDER']):
            if filename.endswith('.bak'):
                file_path = os.path.join(app.config['BACKUP_FOLDER'], filename)
                file_stat = os.stat(file_path)
                size_mb = file_stat.st_size / (1024 * 1024)
                backups.append({
                    'name': filename,
                    'size': f"{size_mb:.2f} MB",
                    'date': datetime.fromtimestamp(file_stat.st_mtime)
                })
    
    # Sort backups by date (newest first)
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('backup.html', backups=backups, message=message, status=status)

# Restore database
@app.route('/admin/restore', methods=['POST'])
@admin_required
def admin_restore():
    backup_file = request.form.get('backup_file')
    
    if not backup_file:
        flash('No backup file selected.')
        return redirect(url_for('admin_backup'))
    
    backup_path = os.path.join(app.config['BACKUP_FOLDER'], backup_file)
    
    if not os.path.exists(backup_path):
        flash('Backup file not found.')
        return redirect(url_for('admin_backup'))
    
    try:
        # Execute database restoration
        # Note: This would typically use direct SQL execution or a stored procedure
        
        # For demonstration, we'll just log the attempt
        log_activity(
            user_id=g.user.UserID,
            action='RESTORE',
            table_name='DATABASE',
            new_values={'FileName': backup_file},
            ip_address=request.remote_addr
        )
        
        flash(f"Database restoration from '{backup_file}' simulated successfully.")
    except Exception as e:
        flash(f"Error restoring database: {str(e)}")
    
    return redirect(url_for('admin_backup'))

# Download backup
@app.route('/admin/backup/download/<filename>')
@admin_required
def admin_download_backup(filename):
    return send_from_directory(
        app.config['BACKUP_FOLDER'],
        filename,
        as_attachment=True
    )

# Delete backup
@app.route('/admin/backup/delete', methods=['POST'])
@admin_required
def admin_delete_backup():
    filename = request.form.get('filename')
    
    if not filename:
        flash('No backup file specified.')
        return redirect(url_for('admin_backup'))
    
    backup_path = os.path.join(app.config['BACKUP_FOLDER'], filename)
    
    if not os.path.exists(backup_path):
        flash('Backup file not found.')
        return redirect(url_for('admin_backup'))
    
    try:
        os.remove(backup_path)
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='DELETE',
            table_name='BACKUP',
            old_values={'FileName': filename},
            ip_address=request.remote_addr
        )
        
        flash(f"Backup file '{filename}' deleted successfully.")
    except Exception as e:
        flash(f"Error deleting backup file: {str(e)}")
    
    return redirect(url_for('admin_backup'))

# Book management routes
@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        publication_year = request.form.get('publication_year')
        publisher = request.form.get('publisher')
        category_id = request.form.get('category_id') or None
        description = request.form.get('description')
        cover_image = request.form.get('cover_image')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create new book
            cursor.execute(
                "INSERT INTO books (Title, Author, ISBN, PublicationYear, Publisher, CategoryID, Status, Description, CoverImage) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                title, author, isbn, publication_year, publisher, category_id, 'Available', description, cover_image
            )
            
            conn.commit()
            
            # Get the book ID of the inserted book
            cursor.execute("SELECT BookID FROM books WHERE ISBN = ?", isbn)
            book_id = cursor.fetchone()[0]
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='INSERT',
                table_name='books',
                record_id=book_id,
                new_values={
                    'Title': title,
                    'Author': author,
                    'ISBN': isbn,
                    'CategoryID': category_id
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Book "{title}" has been added.')
            return redirect(url_for('catalog'))

@app.route('/edit_book/<int:book_id>', methods=['POST'])
@login_required
def edit_book(book_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM books WHERE BookID = ?", book_id)
        book = cursor.fetchone()
        
        if request.method == 'POST':
            # Store old values for logging
            old_values = {
                'Title': book.Title,
                'Author': book.Author,
                'ISBN': book.ISBN,
                'PublicationYear': book.PublicationYear,
                'Publisher': book.Publisher,
                'CategoryID': book.CategoryID,
                'Description': book.Description,
                'CoverImage': book.CoverImage
            }
            
            title = request.form.get('title')
            author = request.form.get('author')
            isbn = request.form.get('isbn')
            publication_year = request.form.get('publication_year') or None
            publisher = request.form.get('publisher')
            category_id = request.form.get('category_id') or None
            description = request.form.get('description')
            cover_image = request.form.get('cover_image')
            
            # Update book details
            cursor.execute(
                "UPDATE books SET Title = ?, Author = ?, ISBN = ?, PublicationYear = ?, Publisher = ?, CategoryID = ?, Description = ?, CoverImage = ? "
                "WHERE BookID = ?",
                title, author, isbn, publication_year, publisher, category_id, description, cover_image, book_id
            )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='UPDATE',
                table_name='books',
                record_id=book_id,
                old_values=old_values,
                new_values={
                    'Title': title,
                    'Author': author,
                    'ISBN': isbn,
                    'PublicationYear': publication_year,
                    'Publisher': publisher,
                    'CategoryID': category_id,
                    'Description': description,
                    'CoverImage': cover_image
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Book "{title}" has been updated.')
        
        return redirect(url_for('view_book', book_id=book_id))

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM books WHERE BookID = ?", book_id)
        book = cursor.fetchone()
        
        # Check if book can be deleted (no active loans)
        cursor.execute("SELECT COUNT(*) FROM loans WHERE BookID = ? AND Status IN ('Borrowed', 'Overdue')", book_id)
        active_loans = cursor.fetchone()[0]
        
        if active_loans > 0:
            flash('Cannot delete book with active loans.')
            return redirect(url_for('view_book', book_id=book_id))
        
        # Store book info for logging
        book_info = {
            'BookID': book.BookID,
            'Title': book.Title,
            'Author': book.Author,
            'ISBN': book.ISBN,
            'Status': book.Status
        }
        
        # Delete book
        cursor.execute("DELETE FROM books WHERE BookID = ?", book_id)
        conn.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='DELETE',
            table_name='books',
            record_id=book_id,
            old_values=book_info,
            ip_address=request.remote_addr
        )
        
        flash(f'Book "{book.Title}" has been deleted.')
        return redirect(url_for('catalog'))

# Loan management routes
@app.route('/issue_book/<int:book_id>', methods=['POST'])
@login_required
def issue_book(book_id):
    if request.method == 'POST':
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM books WHERE BookID = ?", book_id)
            book = cursor.fetchone()
            
            if book.Status != 'Available':
                flash('This book is not available for loan.')
                return redirect(url_for('view_book', book_id=book_id))
            
            member_id = request.form.get('member_id')
            due_date_str = request.form.get('due_date')
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            
            cursor.execute("SELECT * FROM members WHERE MemberID = ?", member_id)
            member = cursor.fetchone()
            
            # Check member eligibility
            if member.Status != 'Active':
                flash('Member is not active and cannot borrow books.')
                return redirect(url_for('view_book', book_id=book_id))
            
            # Check if member has reached maximum loans
            cursor.execute("SELECT COUNT(*) FROM loans WHERE MemberID = ? AND Status IN ('Borrowed', 'Overdue')", member_id)
            active_loans = cursor.fetchone()[0]
            if active_loans >= 5:
                flash('Member has reached the maximum number of loans.')
                return redirect(url_for('view_book', book_id=book_id))
            
            # Create loan record
            cursor.execute(
                "INSERT INTO loans (BookID, MemberID, LoanDate, DueDate, Status) "
                "VALUES (?, ?, ?, ?, ?)",
                book_id, member_id, datetime.now(), due_date, 'Borrowed'
            )
            
            # Update book status
            cursor.execute("UPDATE books SET Status = 'Borrowed' WHERE BookID = ?", book_id)
            
            conn.commit()
            
            # Get the loan ID of the inserted loan
            cursor.execute("SELECT LoanID FROM loans WHERE BookID = ? AND MemberID = ? AND Status = 'Borrowed'", book_id, member_id)
            loan_id = cursor.fetchone()[0]
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='LOAN',
                table_name='loans',
                record_id=loan_id,
                new_values={
                    'BookID': book_id,
                    'MemberID': member_id,
                    'DueDate': due_date_str
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Book "{book.Title}" has been issued to {member.FirstName} {member.LastName}.')
        
        return redirect(url_for('view_book', book_id=book_id))

@app.route('/return_book/<int:book_id>', methods=['POST'])
@login_required
def return_book(book_id):
    if request.method == 'POST':
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM books WHERE BookID = ?", book_id)
            book = cursor.fetchone()
            
            if book.Status not in ['Borrowed', 'Overdue']:
                flash('This book is not currently on loan.')
                return redirect(url_for('view_book', book_id=book_id))
            
            # Find active loan for this book
            cursor.execute("SELECT * FROM loans WHERE BookID = ? AND Status IN ('Borrowed', 'Overdue')", book_id)
            loan = cursor.fetchone()
            
            if not loan:
                flash('No active loan record found for this book.')
                return redirect(url_for('view_book', book_id=book_id))
            
            fine_amount = request.form.get('fine_amount', 0)
            notes = request.form.get('notes', '')
            
            # Update loan record
            cursor.execute(
                "UPDATE loans SET ReturnDate = ?, Status = 'Returned', FineAmount = ?, Notes = ? WHERE LoanID = ?",
                datetime.now(), float(fine_amount), notes, loan.LoanID
            )
            
            # Update book status
            cursor.execute("UPDATE books SET Status = 'Available' WHERE BookID = ?", book_id)
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='RETURN',
                table_name='loans',
                record_id=loan.LoanID,
                new_values={
                    'ReturnDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'FineAmount': fine_amount
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Book "{book.Title}" has been returned.')
        
        return redirect(url_for('view_book', book_id=book_id))

# Member management routes
@app.route('/add_member', methods=['POST'])
@login_required
def add_member():
    if request.method == 'POST':
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        membership_date = datetime.now()
        
        # Calculate expiry date (default 1 year)
        expiry_date_str = request.form.get('expiryDate')
        if expiry_date_str:
            membership_expiry = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        else:
            membership_expiry = datetime.now() + timedelta(days=365)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if email already exists
            cursor.execute("SELECT COUNT(*) FROM members WHERE Email = ?", email)
            if cursor.fetchone()[0] > 0:
                flash('Email already exists.')
                return redirect(url_for('list_members'))
            
            # Create new member
            cursor.execute(
                "INSERT INTO members (FirstName, LastName, Email, Phone, Address, MembershipDate, MembershipExpiry, Status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                first_name, last_name, email, phone, address, membership_date, membership_expiry, 'Active'
            )
            
            conn.commit()
            
            # Get the member ID of the inserted member
            cursor.execute("SELECT MemberID FROM members WHERE Email = ?", email)
            member_id = cursor.fetchone()[0]
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='INSERT',
                table_name='members',
                record_id=member_id,
                new_values={
                    'FirstName': first_name,
                    'LastName': last_name,
                    'Email': email,
                    'MembershipExpiry': membership_expiry.strftime('%Y-%m-%d')
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Member {first_name} {last_name} has been added.')
            return redirect(url_for('list_members'))

@app.route('/edit_member/<int:member_id>', methods=['POST'])
@login_required
def edit_member(member_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM members WHERE MemberID = ?", member_id)
        member = cursor.fetchone()
        
        if request.method == 'POST':
            # Store old values for logging
            old_values = {
                'FirstName': member.FirstName,
                'LastName': member.LastName,
                'Email': member.Email,
                'Phone': member.Phone,
                'Address': member.Address,
                'Status': member.Status,
                'MembershipExpiry': member.MembershipExpiry.strftime('%Y-%m-%d') if member.MembershipExpiry else None
            }
            
            first_name = request.form.get('firstName')
            last_name = request.form.get('lastName')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            status = request.form.get('status')
            
            expiry_date_str = request.form.get('expiryDate')
            if expiry_date_str:
                membership_expiry = datetime.strptime(expiry_date_str, '%Y-%m-%d')
            else:
                membership_expiry = member.MembershipExpiry
            
            # Update member details
            cursor.execute(
                "UPDATE members SET FirstName = ?, LastName = ?, Email = ?, Phone = ?, Address = ?, Status = ?, MembershipExpiry = ? WHERE MemberID = ?",
                first_name, last_name, email, phone, address, status, membership_expiry, member_id
            )
            
            conn.commit()
            
            # Log the activity
            log_activity(
                user_id=g.user.UserID,
                action='UPDATE',
                table_name='members',
                record_id=member_id,
                old_values=old_values,
                new_values={
                    'FirstName': first_name,
                    'LastName': last_name,
                    'Email': email,
                    'Phone': phone,
                    'Address': address,
                    'Status': status,
                    'MembershipExpiry': membership_expiry.strftime('%Y-%m-%d') if membership_expiry else None
                },
                ip_address=request.remote_addr
            )
            
            flash(f'Member {first_name} {last_name} has been updated.')
        
        return redirect(url_for('list_members'))

# Report generation routes
@app.route('/reports')
@admin_required
def reports():
    return render_template('reports.html')

@app.route('/reports/generate', methods=['POST'])
@admin_required
def generate_report():
    report_type = request.form.get('report_type')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else datetime.now()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if report_type == 'popular_books':
            # Get most borrowed books
            cursor.execute(
                "SELECT b.BookID, b.Title, b.Author, COUNT(l.LoanID) AS loan_count "
                "FROM books b "
                "JOIN loans l ON b.BookID = l.BookID "
                "GROUP BY b.BookID, b.Title, b.Author "
                "ORDER BY loan_count DESC"
            )
            book_loans = cursor.fetchall()
            
            return render_template('report_popular_books.html', 
                books=book_loans, start_date=start_date, end_date=end_date)
        
        elif report_type == 'overdue_books':
            # Get overdue books
            cursor.execute(
                "SELECT b.*, m.*, l.* "
                "FROM books b "
                "JOIN loans l ON b.BookID = l.BookID "
                "JOIN members m ON l.MemberID = m.MemberID "
                "WHERE l.Status = 'Overdue'"
            )
            overdue_loans = cursor.fetchall()
            
            return render_template('report_overdue_books.html', 
                overdue_loans=overdue_loans, current_date=datetime.now())
        
        elif report_type == 'member_activity':
            # Get member activity
            cursor.execute(
                "SELECT m.*, COUNT(l.LoanID) AS total_loans, "
                "SUM(CASE WHEN l.Status = 'Overdue' THEN 1 ELSE 0 END) AS overdue_count, "
                "SUM(l.FineAmount) AS total_fines "
                "FROM members m "
                "LEFT JOIN loans l ON m.MemberID = l.MemberID "
                "GROUP BY m.MemberID "
                "ORDER BY total_loans DESC"
            )
            members = cursor.fetchall()
            
            return render_template('report_member_activity.html', 
                members=members, start_date=start_date, end_date=end_date)
        
        flash('Invalid report type selected.')
        return redirect(url_for('reports'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found", details="The requested page does not exist."), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error="Internal server error", details=str(e)), 500

if __name__ == '__main__':
    # Run the initialization code at startup
    initialize_database()
    app.run(debug=True)
