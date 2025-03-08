import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# These classes represent database entities without using an ORM
# They'll be populated using data from direct database queries

class User:
    def __init__(self, user_id=None, username=None, password_hash=None, email=None, 
                 first_name=None, last_name=None, is_active=True, last_login=None):
        self.UserID = user_id
        self.Username = username
        self.PasswordHash = password_hash
        self.Email = email
        self.FirstName = first_name
        self.LastName = last_name
        self.IsActive = is_active
        self.LastLogin = last_login
        self.CreatedAt = datetime.now()
        self.UpdatedAt = datetime.now()
        self.roles = []
        
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.PasswordHash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.PasswordHash, password)
    
    @property
    def FullName(self):
        return f"{self.FirstName} {self.LastName}" if self.FirstName and self.LastName else self.Username
    
    def has_role(self, role_name):
        return role_name in [role.RoleName for role in self.roles]
    
    def __repr__(self):
        return f'<User {self.Username}>'
    
    @classmethod
    def from_row(cls, row):
        """Create a User object from a database row"""
        if not row:
            return None
        
        # Map column names to object properties
        user = cls(
            user_id=row.UserID,
            username=row.Username,
            password_hash=row.PasswordHash,
            email=row.Email,
            first_name=row.FirstName,
            last_name=row.LastName,
            is_active=bool(row.IsActive),
            last_login=row.LastLogin
        )
        return user

class Role:
    def __init__(self, role_id=None, role_name=None, description=None):
        self.RoleID = role_id
        self.RoleName = role_name
        self.Description = description
        self.CreatedAt = datetime.now()
        self.UpdatedAt = datetime.now()
    
    @property
    def Name(self):
        return self.RoleName
    
    def __repr__(self):
        return f'<Role {self.RoleName}>'
    
    @classmethod
    def from_row(cls, row):
        """Create a Role object from a database row"""
        if not row:
            return None
        
        role = cls(
            role_id=row.RoleID,
            role_name=row.RoleName,
            description=row.Description
        )
        return role

class Book:
    def __init__(self, book_id=None, title=None, author=None, isbn=None, 
                 publication_year=None, publisher=None, category_id=None, 
                 status='Available', description=None, cover_image=None):
        self.BookID = book_id
        self.Title = title
        self.Author = author
        self.ISBN = isbn
        self.PublicationYear = publication_year
        self.Publisher = publisher
        self.CategoryID = category_id
        self.Status = status
        self.Description = description
        self.CoverImage = cover_image
        self.CreatedAt = datetime.now()
        self.UpdatedAt = datetime.now()
        self.CategoryName = None  # Will be populated when joined with Category
        self.loans = []  # For storing related loan records
    
    @classmethod
    def from_row(cls, row):
        """Create a Book object from a database row"""
        if not row:
            return None
        
        book = cls(
            book_id=row.BookID,
            title=row.Title,
            author=row.Author,
            isbn=row.ISBN,
            publication_year=row.PublicationYear,
            publisher=row.Publisher,
            category_id=row.CategoryID,
            status=row.Status,
            description=row.Description,
            cover_image=row.CoverImage
        )
        
        # Check if CategoryName exists in the row (for joined queries)
        if hasattr(row, 'CategoryName'):
            book.CategoryName = row.CategoryName
            
        return book

class Category:
    def __init__(self, category_id=None, category_name=None, description=None):
        self.CategoryID = category_id
        self.CategoryName = category_name
        self.Description = description
        self.CreatedAt = datetime.now()
        self.UpdatedAt = datetime.now()
    
    @classmethod
    def from_row(cls, row):
        """Create a Category object from a database row"""
        if not row:
            return None
        
        category = cls(
            category_id=row.CategoryID,
            category_name=row.CategoryName,
            description=row.Description
        )
        return category

class Member:
    def __init__(self, member_id=None, first_name=None, last_name=None, email=None, 
                 phone=None, address=None, membership_date=None, membership_expiry=None, 
                 status='Active', user_id=None):
        self.MemberID = member_id
        self.FirstName = first_name
        self.LastName = last_name
        self.Email = email
        self.Phone = phone
        self.Address = address
        self.MembershipDate = membership_date or datetime.now()
        self.MembershipExpiry = membership_expiry
        self.Status = status
        self.UserID = user_id
        self.CreatedAt = datetime.now()
        self.UpdatedAt = datetime.now()
    
    @property
    def FullName(self):
        return f"{self.FirstName} {self.LastName}"
    
    @classmethod
    def from_row(cls, row):
        """Create a Member object from a database row"""
        if not row:
            return None
        
        member = cls(
            member_id=row.MemberID,
            first_name=row.FirstName,
            last_name=row.LastName,
            email=row.Email,
            phone=row.Phone,
            address=row.Address,
            membership_date=row.MembershipDate,
            membership_expiry=row.MembershipExpiry,
            status=row.Status,
            user_id=row.UserID
        )
        return member

class Loan:
    def __init__(self, loan_id=None, book_id=None, member_id=None, loan_date=None, 
                 due_date=None, return_date=None, status='Borrowed', fine_amount=0.0, notes=None):
        self.LoanID = loan_id
        self.BookID = book_id
        self.MemberID = member_id
        self.LoanDate = loan_date or datetime.now()
        self.DueDate = due_date
        self.ReturnDate = return_date
        self.Status = status
        self.FineAmount = fine_amount
        self.Notes = notes
        self.CreatedAt = datetime.now()
        self.UpdatedAt = datetime.now()
        self.book = None  # Will be populated with Book object
        self.member = None  # Will be populated with Member object
    
    @classmethod
    def from_row(cls, row):
        """Create a Loan object from a database row"""
        if not row:
            return None
        
        loan = cls(
            loan_id=row.LoanID,
            book_id=row.BookID,
            member_id=row.MemberID,
            loan_date=row.LoanDate,
            due_date=row.DueDate,
            return_date=row.ReturnDate,
            status=row.Status,
            fine_amount=row.FineAmount,
            notes=row.Notes
        )
        return loan

class ActivityLog:
    def __init__(self, log_id=None, user_id=None, action=None, table_name=None, 
                 record_id=None, old_values=None, new_values=None, ip_address=None):
        self.LogID = log_id
        self.UserID = user_id
        self.Action = action
        self.TableName = table_name
        self.RecordID = record_id
        self.OldValues = old_values
        self.NewValues = new_values
        self.IPAddress = ip_address
        self.ChangedAt = datetime.now()
        self.Username = None  # Will be populated when joined with User
    
    @classmethod
    def from_row(cls, row):
        """Create an ActivityLog object from a database row"""
        if not row:
            return None
        
        # Parse JSON strings if they exist
        old_values = json.loads(row.OldValues) if row.OldValues else None
        new_values = json.loads(row.NewValues) if row.NewValues else None
        
        log = cls(
            log_id=row.LogID,
            user_id=row.UserID,
            action=row.Action,
            table_name=row.TableName,
            record_id=row.RecordID,
            old_values=old_values,
            new_values=new_values,
            ip_address=row.IPAddress
        )
        
        # Check if Username exists in the row (for joined queries)
        if hasattr(row, 'Username'):
            log.Username = row.Username
            
        return log

# Helper function to log activity - will be used directly by the app with database connection
def log_activity(user_id, action, table_name=None, record_id=None, old_values=None, new_values=None, ip_address=None):
    # This function implementation is now in app.py with direct database access
    pass
