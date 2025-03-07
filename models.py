from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

# Association table for user roles (many-to-many)
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.UserID'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.RoleID'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'
    
    UserID = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(50), unique=True, nullable=False)
    PasswordHash = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    FirstName = db.Column(db.String(50))
    LastName = db.Column(db.String(50))
    IsActive = db.Column(db.Boolean, default=True)
    LastLogin = db.Column(db.DateTime)
    CreatedAt = db.Column(db.DateTime, default=datetime.now)
    UpdatedAt = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Fix the roles relationship - change the loading strategy
    roles = db.relationship('Role', secondary=user_roles, lazy='joined',
                          backref=db.backref('users', lazy=True))
    logs = db.relationship('ActivityLog', backref='user', lazy=True)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.PasswordHash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.PasswordHash, password)
    
    @property
    def Roles(self):
        return ', '.join([role.RoleName for role in self.roles])
    
    def has_role(self, role_name):
        return any(role.RoleName == role_name for role in self.roles)
    
    def __repr__(self):
        return f'<User {self.Username}>'

class Role(db.Model):
    __tablename__ = 'roles'
    
    RoleID = db.Column(db.Integer, primary_key=True)
    RoleName = db.Column(db.String(50), unique=True, nullable=False)
    Description = db.Column(db.String(255))
    CreatedAt = db.Column(db.DateTime, default=datetime.now)
    UpdatedAt = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    @property
    def UserCount(self):
        return len(self.users)
    
    def __repr__(self):
        return f'<Role {self.RoleName}>'

class Book(db.Model):
    __tablename__ = 'books'
    
    BookID = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(255), nullable=False)
    Author = db.Column(db.String(255), nullable=False)
    ISBN = db.Column(db.String(20), unique=True)
    PublicationYear = db.Column(db.Integer)
    Publisher = db.Column(db.String(255))
    CategoryID = db.Column(db.Integer, db.ForeignKey('categories.CategoryID'))
    Status = db.Column(db.String(50), default='Available')
    Description = db.Column(db.Text)
    CoverImage = db.Column(db.String(255))
    CreatedAt = db.Column(db.DateTime, default=datetime.now)
    UpdatedAt = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    category = db.relationship('Category', backref='books')
    loans = db.relationship('Loan', backref='book', lazy=True)
    
    @property
    def CategoryName(self):
        return self.category.CategoryName if self.category else None
    
    def __repr__(self):
        return f'<Book {self.Title}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    CategoryID = db.Column(db.Integer, primary_key=True)
    CategoryName = db.Column(db.String(100), nullable=False)
    Description = db.Column(db.String(255))
    CreatedAt = db.Column(db.DateTime, default=datetime.now)
    UpdatedAt = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Category {self.CategoryName}>'

class Member(db.Model):
    __tablename__ = 'members'
    
    MemberID = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(50), nullable=False)
    LastName = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Phone = db.Column(db.String(20))
    Address = db.Column(db.String(255))
    MembershipDate = db.Column(db.DateTime, default=datetime.now)
    MembershipExpiry = db.Column(db.DateTime)
    Status = db.Column(db.String(50), default='Active')
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'))
    CreatedAt = db.Column(db.DateTime, default=datetime.now)
    UpdatedAt = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    loans = db.relationship('Loan', backref='member', lazy=True)
    user = db.relationship('User', backref='member', uselist=False)
    
    @property
    def FullName(self):
        return f"{self.FirstName} {self.LastName}"
    
    def __repr__(self):
        return f'<Member {self.FullName}>'

class Loan(db.Model):
    __tablename__ = 'loans'
    
    LoanID = db.Column(db.Integer, primary_key=True)
    BookID = db.Column(db.Integer, db.ForeignKey('books.BookID'), nullable=False)
    MemberID = db.Column(db.Integer, db.ForeignKey('members.MemberID'), nullable=False)
    LoanDate = db.Column(db.DateTime, default=datetime.now, nullable=False)
    DueDate = db.Column(db.DateTime, nullable=False)
    ReturnDate = db.Column(db.DateTime)
    Status = db.Column(db.String(50), default='Borrowed')
    FineAmount = db.Column(db.Float, default=0.0)
    CreatedAt = db.Column(db.DateTime, default=datetime.now)
    UpdatedAt = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Loan {self.LoanID}>'

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    LogID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'))
    Action = db.Column(db.String(50), nullable=False)
    TableName = db.Column(db.String(50))
    RecordID = db.Column(db.Integer)
    OldValues = db.Column(db.Text)
    NewValues = db.Column(db.Text)
    IPAddress = db.Column(db.String(50))
    ChangedAt = db.Column(db.DateTime, default=datetime.now)
    
    @property
    def Username(self):
        return self.user.Username if self.user else None
    
    def __repr__(self):
        return f'<ActivityLog {self.Action}>'

def log_activity(user_id, action, table_name=None, record_id=None, old_values=None, new_values=None, ip_address=None):
    """Helper function to log activities"""
    log = ActivityLog(
        UserID=user_id,
        Action=action,
        TableName=table_name,
        RecordID=record_id,
        OldValues=json.dumps(old_values) if old_values else None,
        NewValues=json.dumps(new_values) if new_values else None,
        IPAddress=ip_address
    )
    db.session.add(log)
    db.session.commit()
