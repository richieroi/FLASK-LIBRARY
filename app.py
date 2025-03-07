import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g, session, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func, desc, or_, and_, case

from config import Config
from models import db, User, Role, Book, Category, Member, Loan, ActivityLog, log_activity
from auth import auth, login_required, admin_required

app = Flask(__name__)

# Configure database
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['BACKUP_FOLDER'] = Config.BACKUP_FOLDER
app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME

# Initialize app with Config class
Config.init_app(app)

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')

# Initialize extensions
db.init_app(app)

# Create database tables if they don't exist
@app.before_first_request
def create_tables():
    db.create_all()
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
    
    for role_name in default_roles:
        role = Role.query.filter_by(RoleName=role_name).first()
        if not role:
            role = Role(RoleName=role_name, Description=descriptions.get(role_name))
            db.session.add(role)
    
    db.session.commit()

def create_admin_user():
    # Check if any users exist
    if User.query.count() == 0:
        # Create admin user
        admin = User(
            Username='admin',
            Email='admin@library.com',
            FirstName='Admin',
            LastName='User',
            IsActive=True
        )
        admin.password = 'admin'  # In production, use a strong password
        
        # Assign admin role
        admin_role = Role.query.filter_by(RoleName='Admin').first()
        if admin_role:
            admin.roles.append(admin_role)
        
        db.session.add(admin)
        db.session.commit()
        
        print("Created default admin user: username='admin', password='admin'")

def create_default_categories():
    default_categories = [
        'Fiction', 'Non-Fiction', 'Science Fiction', 'Mystery', 
        'Biography', 'History', 'Children', 'Science', 'Technology',
        'Arts', 'Philosophy', 'Religion', 'Business', 'Travel'
    ]
    
    if Category.query.count() == 0:
        for category_name in default_categories:
            category = Category(CategoryName=category_name)
            db.session.add(category)
        
        db.session.commit()
        print("Created default book categories")

# Index route
@app.route('/')
def index():
    # Get some featured books for the homepage
    # Replace func.random() with func.newid() for SQL Server
    featured_books = Book.query.order_by(func.newid()).limit(6).all()
    now = datetime.now()
    return render_template('index.html', featured_books=featured_books, now=now)

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    # Get statistics for dashboard
    book_count = Book.query.count()
    member_count = Member.query.count()
    active_loans = Loan.query.filter_by(Status='Borrowed').count()
    overdue_loans = Loan.query.filter(Loan.DueDate < datetime.now(), Loan.Status == 'Borrowed').count()
    
    # Recent activities
    recent_activities = ActivityLog.query.order_by(ActivityLog.ChangedAt.desc()).limit(10).all()
    
    # Recent loans
    recent_loans = Loan.query.order_by(Loan.LoanDate.desc()).limit(5).all()
    
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
    # Staff-specific stats and functionality
    book_count = Book.query.count()
    active_loans = Loan.query.filter_by(Status='Borrowed').count()
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
    # Get the member associated with the logged-in user
    member = Member.query.filter_by(UserID=g.user.UserID).first()
    
    if member:
        # Get member's active loans
        active_loans = Loan.query.filter_by(
            MemberID=member.MemberID
        ).filter(Loan.Status.in_(['Borrowed', 'Overdue'])).all()
        
        # Get loan history
        loan_history = Loan.query.filter_by(
            MemberID=member.MemberID, Status='Returned'
        ).order_by(Loan.ReturnDate.desc()).limit(5).all()
        
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
    books = Book.query.all()
    categories = Category.query.all()
    return render_template('catalog.html', books=books, categories=categories)

# Single book view
@app.route('/book/<int:book_id>')
def view_book(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('book_details.html', book=book)

# Member listing
@app.route('/members')
@login_required
def list_members():
    members = Member.query.all()
    return render_template('members.html', members=members)

# Loan listing
@app.route('/loans')
@login_required
def list_loans():
    loans = Loan.query.all()
    return render_template('loans.html', loans=loans)

# User management
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
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
        
        # Check if username or email already exists
        if User.query.filter_by(Username=username).first():
            flash('Username already exists.')
            return redirect(url_for('admin_users'))
        
        if User.query.filter_by(Email=email).first():
            flash('Email already exists.')
            return redirect(url_for('admin_users'))
        
        # Create new user
        user = User(
            Username=username,
            Email=email,
            FirstName=first_name,
            LastName=last_name,
            IsActive=True
        )
        user.password = password
        
        # Assign roles
        for role_name in roles:
            role = Role.query.filter_by(RoleName=role_name).first()
            if role:
                user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='INSERT',
            table_name='users',
            record_id=user.UserID,
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
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Store old values for logging
        old_values = {
            'Email': user.Email,
            'FirstName': user.FirstName,
            'LastName': user.LastName,
            'Roles': user.Roles
        }
        
        user.Email = request.form.get('email')
        user.FirstName = request.form.get('firstName')
        user.LastName = request.form.get('lastName')
        
        # Update roles
        user.roles = []
        role_names = request.form.getlist('roles')
        for role_name in role_names:
            role = Role.query.filter_by(RoleName=role_name).first()
            if role:
                user.roles.append(role)
        
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='UPDATE',
            table_name='users',
            record_id=user.UserID,
            old_values=old_values,
            new_values={
                'Email': user.Email,
                'FirstName': user.FirstName,
                'LastName': user.LastName,
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
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')
        
        if new_password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('admin_users'))
        
        user.password = new_password
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='UPDATE',
            table_name='users',
            record_id=user.UserID,
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
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        old_status = user.IsActive
        user.IsActive = not user.IsActive
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='UPDATE',
            table_name='users',
            record_id=user.UserID,
            old_values={'IsActive': old_status},
            new_values={'IsActive': user.IsActive},
            ip_address=request.remote_addr
        )
        
        status_text = 'enabled' if user.IsActive else 'disabled'
        flash(f'User {user.Username} has been {status_text}.')
    
    return redirect(url_for('admin_users'))

# Role management
@app.route('/admin/roles')
@admin_required
def admin_roles():
    roles = Role.query.all()
    return render_template('roles.html', roles=roles)

# Add role
@app.route('/admin/roles/add', methods=['POST'])
@admin_required
def admin_add_role():
    if request.method == 'POST':
        role_name = request.form.get('roleName')
        description = request.form.get('description')
        
        # Check if role already exists
        if Role.query.filter_by(RoleName=role_name).first():
            flash('Role already exists.')
            return redirect(url_for('admin_roles'))
        
        # Create new role
        role = Role(
            RoleName=role_name,
            Description=description
        )
        
        db.session.add(role)
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='INSERT',
            table_name='roles',
            record_id=role.RoleID,
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
    role = Role.query.get_or_404(role_id)
    
    if request.method == 'POST':
        # Store old values for logging
        old_values = {
            'RoleName': role.RoleName,
            'Description': role.Description
        }
        
        # Check if role is a system role
        system_roles = ['Admin', 'Staff', 'Member', 'Guest']
        if role.RoleName in system_roles:
            # Only update description for system roles
            role.Description = request.form.get('description')
        else:
            role.RoleName = request.form.get('roleName')
            role.Description = request.form.get('description')
        
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='UPDATE',
            table_name='roles',
            record_id=role.RoleID,
            old_values=old_values,
            new_values={
                'RoleName': role.RoleName,
                'Description': role.Description
            },
            ip_address=request.remote_addr
        )
        
        flash(f'Role {role.RoleName} has been updated.')
    
    return redirect(url_for('admin_roles'))

# Delete role
@app.route('/admin/roles/delete/<int:role_id>', methods=['POST'])
@admin_required
def admin_delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    
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
    db.session.delete(role)
    db.session.commit()
    
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
    # Get filter parameters
    action = request.args.get('action')
    table = request.args.get('table')
    user_id = request.args.get('user_id')
    days = request.args.get('days')
    
    # Base query
    query = ActivityLog.query
    
    # Apply filters
    if action:
        query = query.filter(ActivityLog.Action == action)
    
    if table:
        query = query.filter(ActivityLog.TableName == table)
    
    if user_id:
        query = query.filter(ActivityLog.UserID == user_id)
    
    if days:
        days_ago = datetime.now() - timedelta(days=int(days))
        query = query.filter(ActivityLog.ChangedAt >= days_ago)
    
    # Execute query
    logs = query.order_by(ActivityLog.ChangedAt.desc()).all()
    
    # Get unique actions and tables for filters
    actions = db.session.query(ActivityLog.Action).distinct().all()
    tables = db.session.query(ActivityLog.TableName).distinct().all()
    users = User.query.all()
    
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
        
        # Create new book
        book = Book(
            Title=title,
            Author=author,
            ISBN=isbn,
            PublicationYear=publication_year,
            Publisher=publisher,
            CategoryID=category_id,
            Status='Available',
            Description=description,
            CoverImage=cover_image
        )
        
        db.session.add(book)
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='INSERT',
            table_name='books',
            record_id=book.BookID,
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
    book = Book.query.get_or_404(book_id)
    categories = Category.query.all()
    
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
        
        # Update book details
        book.Title = request.form.get('title')
        book.Author = request.form.get('author')
        book.ISBN = request.form.get('isbn')
        book.PublicationYear = request.form.get('publication_year') or None
        book.Publisher = request.form.get('publisher')
        book.CategoryID = request.form.get('category_id') or None
        book.Description = request.form.get('description')
        book.CoverImage = request.form.get('cover_image')
        
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='UPDATE',
            table_name='books',
            record_id=book.BookID,
            old_values=old_values,
            new_values={
                'Title': book.Title,
                'Author': book.Author,
                'ISBN': book.ISBN,
                'PublicationYear': book.PublicationYear,
                'Publisher': book.Publisher,
                'CategoryID': book.CategoryID,
                'Description': book.Description,
                'CoverImage': book.CoverImage
            },
            ip_address=request.remote_addr
        )
        
        flash(f'Book "{book.Title}" has been updated.')
    
    return redirect(url_for('view_book', book_id=book.BookID))

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if book can be deleted (no active loans)
    active_loans = Loan.query.filter_by(BookID=book_id).filter(Loan.Status.in_(['Borrowed', 'Overdue'])).count()
    
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
    db.session.delete(book)
    db.session.commit()
    
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
        book = Book.query.get_or_404(book_id)
        
        if book.Status != 'Available':
            flash('This book is not available for loan.')
            return redirect(url_for('view_book', book_id=book_id))
        
        member_id = request.form.get('member_id')
        due_date_str = request.form.get('due_date')
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        member = Member.query.get_or_404(member_id)
        
        # Check member eligibility
        if member.Status != 'Active':
            flash('Member is not active and cannot borrow books.')
            return redirect(url_for('view_book', book_id=book_id))
        
        # Check if member has reached maximum loans
        active_loans = Loan.query.filter_by(MemberID=member_id).filter(Loan.Status.in_(['Borrowed', 'Overdue'])).count()
        if active_loans >= 5:
            flash('Member has reached the maximum number of loans.')
            return redirect(url_for('view_book', book_id=book_id))
        
        # Create loan record
        loan = Loan(
            BookID=book_id,
            MemberID=member_id,
            LoanDate=datetime.now(),
            DueDate=due_date,
            Status='Borrowed'
        )
        
        # Update book status
        book.Status = 'Borrowed'
        
        db.session.add(loan)
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='LOAN',
            table_name='loans',
            record_id=loan.LoanID,
            new_values={
                'BookID': book_id,
                'MemberID': member_id,
                'DueDate': due_date_str
            },
            ip_address=request.remote_addr
        )
        
        flash(f'Book "{book.Title}" has been issued to {member.FullName}.')
    
    return redirect(url_for('view_book', book_id=book_id))

@app.route('/return_book/<int:book_id>', methods=['POST'])
@login_required
def return_book(book_id):
    if request.method == 'POST':
        book = Book.query.get_or_404(book_id)
        
        if book.Status not in ['Borrowed', 'Overdue']:
            flash('This book is not currently on loan.')
            return redirect(url_for('view_book', book_id=book_id))
        
        # Find active loan for this book
        loan = Loan.query.filter_by(BookID=book_id).filter(Loan.Status.in_(['Borrowed', 'Overdue'])).first()
        
        if not loan:
            flash('No active loan record found for this book.')
            return redirect(url_for('view_book', book_id=book_id))
        
        fine_amount = request.form.get('fine_amount', 0)
        notes = request.form.get('notes', '')
        
        # Update loan record
        loan.ReturnDate = datetime.now()
        loan.Status = 'Returned'
        loan.FineAmount = float(fine_amount)
        loan.Notes = notes
        
        # Update book status
        book.Status = 'Available'
        
        db.session.commit()
        
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
        
        # Check if email already exists
        if Member.query.filter_by(Email=email).first():
            flash('Email already exists.')
            return redirect(url_for('list_members'))
        
        # Create new member
        member = Member(
            FirstName=first_name,
            LastName=last_name,
            Email=email,
            Phone=phone,
            Address=address,
            MembershipDate=membership_date,
            MembershipExpiry=membership_expiry,
            Status='Active'
        )
        
        db.session.add(member)
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='INSERT',
            table_name='members',
            record_id=member.MemberID,
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
    member = Member.query.get_or_404(member_id)
    
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
        
        # Update member details
        member.FirstName = request.form.get('firstName')
        member.LastName = request.form.get('lastName')
        member.Email = request.form.get('email')
        member.Phone = request.form.get('phone')
        member.Address = request.form.get('address')
        member.Status = request.form.get('status')
        
        expiry_date_str = request.form.get('expiryDate')
        if expiry_date_str:
            member.MembershipExpiry = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        
        db.session.commit()
        
        # Log the activity
        log_activity(
            user_id=g.user.UserID,
            action='UPDATE',
            table_name='members',
            record_id=member.MemberID,
            old_values=old_values,
            new_values={
                'FirstName': member.FirstName,
                'LastName': member.LastName,
                'Email': member.Email,
                'Phone': member.Phone,
                'Address': member.Address,
                'Status': member.Status,
                'MembershipExpiry': member.MembershipExpiry.strftime('%Y-%m-%d') if member.MembershipExpiry else None
            },
            ip_address=request.remote_addr
        )
        
        flash(f'Member {member.FullName} has been updated.')
    
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
    
    if report_type == 'popular_books':
        # Get most borrowed books
        book_loans = db.session.query(
            Book.BookID, Book.Title, Book.Author, func.count(Loan.LoanID).label('loan_count')
        ).join(Loan, Book.BookID == Loan.BookID).group_by(
            Book.BookID, Book.Title, Book.Author
        ).order_by(desc('loan_count')).all()
        
        return render_template('report_popular_books.html', 
            books=book_loans, start_date=start_date, end_date=end_date)
    
    elif report_type == 'overdue_books':
        # Get overdue books
        overdue_loans = db.session.query(
            Book, Member, Loan
        ).join(Loan, Book.BookID == Loan.BookID
        ).join(Member, Loan.MemberID == Member.MemberID
        ).filter(Loan.Status == 'Overdue').all()
        
        return render_template('report_overdue_books.html', 
            overdue_loans=overdue_loans, current_date=datetime.now())
    
    elif report_type == 'member_activity':
        # Get member activity
        members = db.session.query(
            Member,
            func.count(Loan.LoanID).label('total_loans'),
            func.sum(case((Loan.Status == 'Overdue', 1), else_=0)).label('overdue_count'),
            func.sum(Loan.FineAmount).label('total_fines')
        ).outerjoin(Loan, Member.MemberID == Loan.MemberID
        ).group_by(Member.MemberID
        ).order_by(desc('total_loans')).all()
        
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
    app.run(debug=True)
